import re
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session
from . import models, schemas


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.strip().lower()).strip('-')
    return slug or 'organisation'


def create_organisation(db: Session, name: str, contact_email: str | None = None):
    base_slug = _slugify(name)
    slug = base_slug
    suffix = 2
    while db.query(models.Organisation).filter(models.Organisation.slug == slug).first():
        slug = f'{base_slug}-{suffix}'
        suffix += 1

    organisation = models.Organisation(name=name, slug=slug, contact_email=contact_email)
    db.add(organisation)
    db.flush()
    return organisation


def _tenant_filter(query, model, organisation_id: int | None):
    if organisation_id is None or not hasattr(model, 'organisation_id'):
        return query
    return query.filter(model.organisation_id == organisation_id)


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email, models.User.is_deleted.is_(False)).first()


def create_user(
    db: Session,
    email: str,
    full_name: str | None,
    hashed_password: str,
    role: str = 'officer',
    created_by: int | None = None,
    organisation_id: int | None = None,
):
    db_user = models.User(
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        created_by=created_by,
        updated_by=created_by,
        organisation_id=organisation_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_patrol(db: Session, patrol_id: int, organisation_id: int | None = None):
    query = db.query(models.Patrol).filter(models.Patrol.id == patrol_id, models.Patrol.is_deleted.is_(False))
    return _tenant_filter(query, models.Patrol, organisation_id).first()


def get_patrols(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.Patrol).filter(models.Patrol.is_deleted.is_(False))
    return _tenant_filter(query, models.Patrol, organisation_id).offset(skip).limit(limit).all()


def create_patrol(
    db: Session,
    patrol: schemas.PatrolCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_patrol = models.Patrol(
        name=patrol.name,
        description=patrol.description,
        start_time=patrol.start_time,
        end_time=patrol.end_time,
        assigned_to=patrol.assigned_to,
        created_by=actor_user_id,
        updated_by=actor_user_id,
        organisation_id=organisation_id,
    )
    db.add(db_patrol)
    db.commit()
    db.refresh(db_patrol)
    return db_patrol


def update_patrol(
    db: Session,
    patrol_id: int,
    patrol_update: schemas.PatrolCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_patrol = get_patrol(db, patrol_id, organisation_id)
    if not db_patrol:
        return None
    db_patrol.name = patrol_update.name
    db_patrol.description = patrol_update.description
    db_patrol.start_time = patrol_update.start_time
    db_patrol.end_time = patrol_update.end_time
    db_patrol.assigned_to = patrol_update.assigned_to
    db_patrol.updated_by = actor_user_id
    db.commit()
    db.refresh(db_patrol)
    return db_patrol


def delete_patrol(
    db: Session,
    patrol_id: int,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_patrol = get_patrol(db, patrol_id, organisation_id)
    if db_patrol:
        db_patrol.is_deleted = True
        db_patrol.updated_by = actor_user_id
        db.commit()
    return db_patrol


def get_patrol_logs(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.PatrolLog).order_by(models.PatrolLog.timestamp.desc())
    return _tenant_filter(query, models.PatrolLog, organisation_id).offset(skip).limit(limit).all()


def create_patrol_log(
    db: Session,
    patrol_log: schemas.PatrolLogCreate,
    user_id: int,
    organisation_id: int | None = None,
):
    db_patrol_log = models.PatrolLog(
        user_id=user_id,
        location=patrol_log.location,
        status=patrol_log.status,
        timestamp=patrol_log.timestamp or datetime.now(timezone.utc),
        organisation_id=organisation_id,
    )
    db.add(db_patrol_log)
    db.commit()
    db.refresh(db_patrol_log)
    return db_patrol_log


def get_incidents(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.Incident).order_by(models.Incident.timestamp.desc())
    return _tenant_filter(query, models.Incident, organisation_id).offset(skip).limit(limit).all()


def create_incident(
    db: Session,
    incident: schemas.IncidentCreate,
    user_id: int,
    organisation_id: int | None = None,
):
    db_incident = models.Incident(
        user_id=user_id,
        description=incident.description,
        severity=incident.severity,
        timestamp=incident.timestamp or datetime.now(timezone.utc),
        organisation_id=organisation_id,
    )
    db.add(db_incident)
    db.commit()
    db.refresh(db_incident)
    return db_incident


def get_device(db: Session, device_id: int, organisation_id: int | None = None):
    query = db.query(models.Device).filter(models.Device.id == device_id, models.Device.is_deleted.is_(False))
    return _tenant_filter(query, models.Device, organisation_id).first()


def get_devices(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.Device).filter(models.Device.is_deleted.is_(False))
    return _tenant_filter(query, models.Device, organisation_id).offset(skip).limit(limit).all()


def create_device(
    db: Session,
    device: schemas.DeviceCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_device = models.Device(
        name=device.name,
        serial_number=device.serial_number,
        status=device.status,
        created_by=actor_user_id,
        updated_by=actor_user_id,
        organisation_id=organisation_id,
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def update_device(
    db: Session,
    device_id: int,
    device_update: schemas.DeviceCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_device = get_device(db, device_id, organisation_id)
    if not db_device:
        return None
    db_device.name = device_update.name
    db_device.serial_number = device_update.serial_number
    db_device.status = device_update.status
    db_device.updated_by = actor_user_id
    db.commit()
    db.refresh(db_device)
    return db_device


def delete_device(
    db: Session,
    device_id: int,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_device = get_device(db, device_id, organisation_id)
    if db_device:
        db_device.is_deleted = True
        db_device.updated_by = actor_user_id
        db.commit()
    return db_device


def get_customer(db: Session, customer_id: int, organisation_id: int | None = None):
    query = db.query(models.Customer).filter(models.Customer.id == customer_id, models.Customer.is_deleted.is_(False))
    return _tenant_filter(query, models.Customer, organisation_id).first()


def get_customers(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.Customer).filter(models.Customer.is_deleted.is_(False))
    return _tenant_filter(query, models.Customer, organisation_id).offset(skip).limit(limit).all()


def create_customer(
    db: Session,
    customer: schemas.CustomerCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_customer = models.Customer(
        name=customer.name,
        contact_email=customer.contact_email,
        phone=customer.phone,
        address=customer.address,
        created_by=actor_user_id,
        updated_by=actor_user_id,
        organisation_id=organisation_id,
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def update_customer(
    db: Session,
    customer_id: int,
    customer_update: schemas.CustomerCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_customer = get_customer(db, customer_id, organisation_id)
    if not db_customer:
        return None
    db_customer.name = customer_update.name
    db_customer.contact_email = customer_update.contact_email
    db_customer.phone = customer_update.phone
    db_customer.address = customer_update.address
    db_customer.updated_by = actor_user_id
    db.commit()
    db.refresh(db_customer)
    return db_customer


def delete_customer(
    db: Session,
    customer_id: int,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_customer = get_customer(db, customer_id, organisation_id)
    if db_customer:
        db_customer.is_deleted = True
        db_customer.updated_by = actor_user_id
        db.commit()
    return db_customer


def get_alert(db: Session, alert_id: int, organisation_id: int | None = None):
    query = db.query(models.Alert).filter(models.Alert.id == alert_id, models.Alert.is_deleted.is_(False))
    return _tenant_filter(query, models.Alert, organisation_id).first()


def get_alerts(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.Alert).filter(models.Alert.is_deleted.is_(False))
    return _tenant_filter(query, models.Alert, organisation_id).offset(skip).limit(limit).all()


def create_alert(
    db: Session,
    alert: schemas.AlertCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_alert = models.Alert(
        title=alert.title,
        description=alert.description,
        severity=alert.severity,
        status=alert.status,
        reported_at=alert.reported_at,
        patrol_id=alert.patrol_id,
        device_id=alert.device_id,
        customer_id=alert.customer_id,
        created_by=actor_user_id,
        updated_by=actor_user_id,
        organisation_id=organisation_id,
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


def update_alert(
    db: Session,
    alert_id: int,
    alert_update: schemas.AlertCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_alert = get_alert(db, alert_id, organisation_id)
    if not db_alert:
        return None
    db_alert.title = alert_update.title
    db_alert.description = alert_update.description
    db_alert.severity = alert_update.severity
    db_alert.status = alert_update.status
    db_alert.reported_at = alert_update.reported_at
    db_alert.patrol_id = alert_update.patrol_id
    db_alert.device_id = alert_update.device_id
    db_alert.customer_id = alert_update.customer_id
    db_alert.updated_by = actor_user_id
    db.commit()
    db.refresh(db_alert)
    return db_alert


def delete_alert(
    db: Session,
    alert_id: int,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_alert = get_alert(db, alert_id, organisation_id)
    if db_alert:
        db_alert.is_deleted = True
        db_alert.updated_by = actor_user_id
        db.commit()
    return db_alert


def get_checkpoint(db: Session, checkpoint_id: int, organisation_id: int | None = None):
    query = db.query(models.Checkpoint).filter(
        models.Checkpoint.id == checkpoint_id,
        models.Checkpoint.is_deleted.is_(False),
    )
    return _tenant_filter(query, models.Checkpoint, organisation_id).first()


def get_checkpoints(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.Checkpoint).filter(models.Checkpoint.is_deleted.is_(False))
    return _tenant_filter(query, models.Checkpoint, organisation_id).offset(skip).limit(limit).all()


def create_checkpoint(
    db: Session,
    checkpoint: schemas.CheckpointCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_checkpoint = models.Checkpoint(
        name=checkpoint.name,
        code=checkpoint.code,
        patrol_id=checkpoint.patrol_id,
        location_label=checkpoint.location_label,
        latitude=checkpoint.latitude,
        longitude=checkpoint.longitude,
        nfc_tag=checkpoint.nfc_tag,
        status=checkpoint.status,
        created_by=actor_user_id,
        updated_by=actor_user_id,
        organisation_id=organisation_id,
    )
    db.add(db_checkpoint)
    db.commit()
    db.refresh(db_checkpoint)
    return db_checkpoint


def verify_checkpoint(
    db: Session,
    checkpoint_id: int,
    payload: schemas.CheckpointVerify,
    actor_user_id: int,
    organisation_id: int | None = None,
):
    db_checkpoint = get_checkpoint(db, checkpoint_id, organisation_id)
    if not db_checkpoint:
        return None
    db_checkpoint.status = 'verified'
    db_checkpoint.verified_at = datetime.now(timezone.utc)
    db_checkpoint.verified_by = actor_user_id
    db_checkpoint.updated_by = actor_user_id
    if payload.latitude is not None:
        db_checkpoint.latitude = payload.latitude
    if payload.longitude is not None:
        db_checkpoint.longitude = payload.longitude
    db.commit()
    db.refresh(db_checkpoint)
    return db_checkpoint


def create_officer_location(
    db: Session,
    location: schemas.OfficerLocationCreate,
    actor_user_id: int,
    organisation_id: int | None = None,
):
    db_location = models.OfficerLocation(
        officer_user_id=actor_user_id,
        patrol_id=location.patrol_id,
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy_meters=location.accuracy_meters,
        battery_level=location.battery_level,
        recorded_at=location.recorded_at or datetime.now(timezone.utc),
        organisation_id=organisation_id,
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


def get_latest_officer_locations(db: Session, organisation_id: int | None = None, limit: int = 100):
    query = db.query(models.OfficerLocation).order_by(models.OfficerLocation.recorded_at.desc())
    query = _tenant_filter(query, models.OfficerLocation, organisation_id)
    latest_by_officer = {}
    for location in query.limit(limit * 5).all():
        if location.officer_user_id not in latest_by_officer:
            latest_by_officer[location.officer_user_id] = location
        if len(latest_by_officer) >= limit:
            break
    return list(latest_by_officer.values())


def get_notifications(
    db: Session,
    user_id: int,
    organisation_id: int | None = None,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Notification).filter(models.Notification.is_deleted.is_(False))
    query = _tenant_filter(query, models.Notification, organisation_id)
    query = query.filter(
        (models.Notification.recipient_user_id == user_id)
        | (models.Notification.recipient_user_id.is_(None))
    )
    if unread_only:
        query = query.filter(models.Notification.read_at.is_(None))
    return query.order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()


def create_notification(
    db: Session,
    notification: schemas.NotificationCreate,
    actor_user_id: int | None = None,
    organisation_id: int | None = None,
):
    db_notification = models.Notification(
        title=notification.title,
        body=notification.body,
        category=notification.category,
        priority=notification.priority,
        recipient_user_id=notification.recipient_user_id,
        created_by=actor_user_id,
        updated_by=actor_user_id,
        organisation_id=organisation_id,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def mark_notification_read(
    db: Session,
    notification_id: int,
    user_id: int,
    organisation_id: int | None = None,
):
    query = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.is_deleted.is_(False),
        (
            (models.Notification.recipient_user_id == user_id)
            | (models.Notification.recipient_user_id.is_(None))
        ),
    )
    notification = _tenant_filter(query, models.Notification, organisation_id).first()
    if not notification:
        return None
    notification.read_at = datetime.now(timezone.utc)
    notification.updated_by = user_id
    db.commit()
    db.refresh(notification)
    return notification


def get_audit_logs(db: Session, skip: int = 0, limit: int = 100, organisation_id: int | None = None):
    query = db.query(models.AuditLog)
    if organisation_id is not None:
        user_ids = db.query(models.User.id).filter(models.User.organisation_id == organisation_id)
        query = query.filter(models.AuditLog.actor_user_id.in_(user_ids))
    return (
        query
        .order_by(models.AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_operations_summary(db: Session, organisation_id: int | None = None):
    def scoped_count(model, *criteria):
        query = db.query(func.count(model.id)).filter(*criteria)
        return _tenant_filter(query, model, organisation_id).scalar() or 0

    officer_query = db.query(func.count(models.User.id)).filter(models.User.is_deleted.is_(False))
    if organisation_id is not None:
        officer_query = officer_query.filter(models.User.organisation_id == organisation_id)

    notification_query = db.query(func.count(models.Notification.id)).filter(
        models.Notification.is_deleted.is_(False),
        models.Notification.read_at.is_(None),
    )
    notification_query = _tenant_filter(notification_query, models.Notification, organisation_id)

    return {
        'active_patrols': scoped_count(models.Patrol, models.Patrol.is_deleted.is_(False)),
        'open_incidents': scoped_count(
            models.Alert,
            models.Alert.is_deleted.is_(False),
            models.Alert.status.in_(['open', 'investigating', 'pending']),
        ),
        'active_devices': scoped_count(
            models.Device,
            models.Device.is_deleted.is_(False),
            models.Device.status == 'active',
        ),
        'customers': scoped_count(models.Customer, models.Customer.is_deleted.is_(False)),
        'officers': officer_query.scalar() or 0,
        'pending_checkpoints': scoped_count(
            models.Checkpoint,
            models.Checkpoint.is_deleted.is_(False),
            models.Checkpoint.status == 'pending',
        ),
        'unread_notifications': notification_query.scalar() or 0,
        'recent_activity': get_audit_logs(db, skip=0, limit=8, organisation_id=organisation_id),
    }


def get_analytics_report(db: Session, organisation_id: int | None = None):
    def scoped_count(model, *criteria):
        query = db.query(func.count(model.id)).filter(*criteria)
        return _tenant_filter(query, model, organisation_id).scalar() or 0

    return {
        'active_patrols': scoped_count(
            models.Patrol,
            models.Patrol.is_deleted.is_(False),
            models.Patrol.end_time.is_(None),
        ),
        'completed_patrols': scoped_count(
            models.Patrol,
            models.Patrol.is_deleted.is_(False),
            models.Patrol.end_time.is_not(None),
        ),
        'open_incidents': scoped_count(
            models.Alert,
            models.Alert.is_deleted.is_(False),
            models.Alert.status.in_(['open', 'investigating', 'pending']),
        ),
        'critical_incidents': scoped_count(
            models.Alert,
            models.Alert.is_deleted.is_(False),
            models.Alert.severity.in_(['critical', 'high']),
        ),
        'pending_checkpoints': scoped_count(
            models.Checkpoint,
            models.Checkpoint.is_deleted.is_(False),
            models.Checkpoint.status == 'pending',
        ),
        'verified_checkpoints': scoped_count(
            models.Checkpoint,
            models.Checkpoint.is_deleted.is_(False),
            models.Checkpoint.status == 'verified',
        ),
        'active_devices': scoped_count(
            models.Device,
            models.Device.is_deleted.is_(False),
            models.Device.status == 'active',
        ),
        'latest_locations': get_latest_officer_locations(db, organisation_id=organisation_id, limit=25),
    }
