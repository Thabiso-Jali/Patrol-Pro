from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app import models
from backend.app.database import Base
from backend.app.domain.registry import DOMAIN_OBJECT_OWNERS, DomainObjectType
from backend.app.domain.errors import DomainError, ImmutableRecord
from backend.app.domain.states import InvalidStateTransition, assert_mutable, assert_transition
from backend.app.services.domain_registry import register_domain_object, require_domain_object
from backend.app.services.evidence import link_evidence
from backend.app.services.operational_events import append_operational_event
from backend.app.services.workforce_credentials import assign_qualification
from backend.app.services.workforce_scheduling import declare_availability, request_leave
from backend.app.services.tenant_validation import aggregate_mutation


@pytest.fixture()
def domain_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def organisation(domain_db, name):
    record = models.Organisation(name=name, slug=name.lower(), timezone='UTC')
    domain_db.add(record)
    domain_db.flush()
    return record


def test_every_phase1_model_declares_aggregate_and_owning_service():
    phase1_models = (
        models.DomainObject, models.Employee, models.Contact, models.Site, models.SiteAsset,
        models.CompanyPolicy, models.PostOrder, models.PostOrderVersion,
        models.PostOrderAcknowledgement, models.Qualification, models.EmployeeQualification,
        models.Licence, models.AvailabilityPeriod, models.LeavePeriod, models.Shift,
        models.ShiftAssignment, models.PatrolTemplate, models.PatrolTemplateCheckpoint,
        models.CheckpointVerificationEvent, models.OperationalAlert,
        models.EvidenceAttachment, models.EvidenceLink, models.DailyActivityReport,
        models.OperationalEventSubject,
    )
    for model in phase1_models:
        assert model.__aggregate_root__
        assert model.__owning_service__


def test_registry_is_shared_and_tenant_scoped(domain_db):
    first = organisation(domain_db, 'First')
    second = organisation(domain_db, 'Second')
    registered = register_domain_object(
        domain_db,
        organisation_id=first.id,
        object_type=DomainObjectType.ORGANISATION,
        object_id=first.id,
    )
    assert registered.owning_service == DOMAIN_OBJECT_OWNERS[DomainObjectType.ORGANISATION][1]
    with pytest.raises(DomainError):
        require_domain_object(
            domain_db, organisation_id=second.id, domain_object_id=registered.id
        )


def test_operational_event_store_is_append_only_and_supports_multiple_subjects(domain_db):
    org = organisation(domain_db, 'Events')
    primary = register_domain_object(
        domain_db, organisation_id=org.id,
        object_type=DomainObjectType.ORGANISATION, object_id=org.id,
    )
    customer = models.Customer(name='Event Customer', organisation_id=org.id)
    domain_db.add(customer)
    domain_db.flush()
    site = models.Site(
        organisation_id=org.id, customer_id=customer.id, name='Event Site',
        address='1 Event Road', timezone='UTC', status='active',
    )
    with aggregate_mutation(domain_db, 'sites'):
        domain_db.add(site)
        domain_db.flush()
    secondary = register_domain_object(
        domain_db, organisation_id=org.id,
        object_type=DomainObjectType.SITE, object_id=site.id,
    )
    event = append_operational_event(
        domain_db,
        organisation_id=org.id,
        action='site.reviewed',
        domain_object_id=primary.id,
        subject_domain_object_ids=(secondary.id,),
        event_metadata={'result': 'accepted'},
    )
    domain_db.flush()
    assert event.event_kind == 'operational'
    assert event.entity_type == 'organisation'
    assert domain_db.query(models.OperationalEventSubject).filter_by(
        operational_event_id=event.id, domain_object_id=secondary.id
    ).one()


def test_evidence_cannot_link_across_organisations(domain_db):
    first = organisation(domain_db, 'EvidenceOne')
    second = organisation(domain_db, 'EvidenceTwo')
    target = register_domain_object(
        domain_db, organisation_id=first.id,
        object_type=DomainObjectType.ORGANISATION, object_id=first.id,
    )
    attachment = models.EvidenceAttachment(
        organisation_id=second.id,
        storage_key='test/evidence',
        original_filename='evidence.jpg', media_type='image/jpeg',
        byte_size=10, content_hash='fake-hash', status='available',
    )
    with aggregate_mutation(domain_db, 'evidence'):
        domain_db.add(attachment)
        domain_db.flush()
    with pytest.raises(DomainError):
        link_evidence(
            domain_db, organisation_id=second.id,
            evidence_attachment_id=attachment.id,
            domain_object_id=target.id, linked_by_employee_id=None,
        )


def test_state_machines_reject_impossible_transitions_and_mutation():
    assert_transition('patrol_occurrence', 'scheduled', 'in_progress')
    with pytest.raises(InvalidStateTransition):
        assert_transition('patrol_occurrence', 'scheduled', 'completed')
    with pytest.raises(ImmutableRecord):
        assert_mutable('patrol_occurrence', 'completed')


def test_canonical_relationships_use_independent_shift_and_occurrence(domain_db):
    org = organisation(domain_db, 'Relationships')
    customer = models.Customer(name='Customer', organisation_id=org.id)
    domain_db.add(customer)
    domain_db.flush()
    site = models.Site(
        organisation_id=org.id, customer_id=customer.id, name='Main Site',
        address='1 Example Road', timezone='UTC', staffing_requirement=1,
        status='active', source_kind='native',
    )
    with aggregate_mutation(domain_db, 'sites'):
        domain_db.add(site)
        domain_db.flush()
    shift = models.Shift(
        organisation_id=org.id, site_id=site.id, name='Day',
        starts_at=datetime.now(timezone.utc), ends_at=datetime.now(timezone.utc),
        status='draft',
    )
    with aggregate_mutation(domain_db, 'shifts'):
        domain_db.add(shift)
        domain_db.flush()
    occurrence = models.Patrol(
        organisation_id=org.id, name='Perimeter', shift_id=shift.id,
        lifecycle_status='scheduled', required_officers=1,
    )
    domain_db.add(occurrence)
    domain_db.flush()
    assert occurrence.shift_id == shift.id
    assert not hasattr(models.ShiftAssignment, 'patrol_id')


def test_internal_workforce_services_enforce_tenant_and_time_boundaries(domain_db):
    first = organisation(domain_db, 'WorkforceOne')
    second = organisation(domain_db, 'WorkforceTwo')
    employee = models.Employee(
        organisation_id=first.id, employee_identifier='PP-1', display_name='Employee',
        employment_role='security_officer', status='active', source_kind='native',
    )
    qualification = models.Qualification(
        organisation_id=first.id, code='FIRST-AID', name='First Aid', status='active',
    )
    with aggregate_mutation(domain_db, 'employees'):
        domain_db.add(employee)
        domain_db.flush()
    with aggregate_mutation(domain_db, 'workforce_credentials'):
        domain_db.add(qualification)
        domain_db.flush()
    assert assign_qualification(
        domain_db, organisation_id=first.id, employee_id=employee.id,
        qualification_id=qualification.id,
    ).employee_id == employee.id
    with pytest.raises(DomainError):
        assign_qualification(
            domain_db, organisation_id=second.id, employee_id=employee.id,
            qualification_id=qualification.id,
        )
    now = datetime.now(timezone.utc)
    assert declare_availability(
        domain_db, organisation_id=first.id, employee_id=employee.id,
        starts_at=now, ends_at=now + timedelta(hours=8),
    ).status == 'proposed'
    with pytest.raises(ValueError):
        request_leave(
            domain_db, organisation_id=first.id, employee_id=employee.id,
            starts_at=now, ends_at=now,
        )
