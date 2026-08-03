from enum import StrEnum


class DomainObjectType(StrEnum):
    ORGANISATION = 'organisation'
    CUSTOMER = 'customer'
    SITE = 'site'
    CONTACT = 'contact'
    EMPLOYEE = 'employee'
    TEAM = 'team'
    SHIFT = 'shift'
    PATROL_TEMPLATE = 'patrol_template'
    PATROL_OCCURRENCE = 'patrol_occurrence'
    CHECKPOINT = 'checkpoint'
    CHECKPOINT_VERIFICATION = 'checkpoint_verification'
    INCIDENT = 'incident'
    OPERATIONAL_ALERT = 'operational_alert'
    NOTIFICATION = 'notification'
    EVIDENCE = 'evidence'
    DAILY_ACTIVITY_REPORT = 'daily_activity_report'
    POST_ORDER = 'post_order'
    SITE_ASSET = 'site_asset'
    COMPANY_POLICY = 'company_policy'


# Aggregate root and canonical owning service. Generic relationships must use
# this registry rather than accepting arbitrary table/model names.
DOMAIN_OBJECT_OWNERS = {
    DomainObjectType.ORGANISATION: ('organisation', 'organisations'),
    DomainObjectType.CUSTOMER: ('customer', 'customers'),
    DomainObjectType.SITE: ('site', 'sites'),
    DomainObjectType.CONTACT: ('customer_or_site', 'contacts'),
    DomainObjectType.EMPLOYEE: ('employee', 'employees'),
    DomainObjectType.TEAM: ('team', 'teams'),
    DomainObjectType.SHIFT: ('shift', 'shifts'),
    DomainObjectType.PATROL_TEMPLATE: ('patrol_template', 'patrol_templates'),
    DomainObjectType.PATROL_OCCURRENCE: ('patrol_occurrence', 'patrol_occurrences'),
    DomainObjectType.CHECKPOINT: ('site', 'checkpoints'),
    DomainObjectType.CHECKPOINT_VERIFICATION: ('patrol_occurrence', 'checkpoint_verifications'),
    DomainObjectType.INCIDENT: ('incident', 'incidents'),
    DomainObjectType.OPERATIONAL_ALERT: ('operational_alert', 'operational_alerts'),
    DomainObjectType.NOTIFICATION: ('notification', 'notifications'),
    DomainObjectType.EVIDENCE: ('evidence', 'evidence'),
    DomainObjectType.DAILY_ACTIVITY_REPORT: ('daily_activity_report', 'daily_activity_reports'),
    DomainObjectType.POST_ORDER: ('site', 'post_orders'),
    DomainObjectType.SITE_ASSET: ('site', 'sites'),
    DomainObjectType.COMPANY_POLICY: ('organisation', 'company_policies'),
}


def canonical_aggregate_root_id(object_type: DomainObjectType, source) -> int:
    """Derive registry ownership from persisted relationships, never caller input."""
    if object_type == DomainObjectType.CONTACT:
        return source.customer_id if source.customer_id is not None else source.site_id
    attribute_by_type = {
        DomainObjectType.CHECKPOINT: 'site_id',
        DomainObjectType.CHECKPOINT_VERIFICATION: 'patrol_occurrence_id',
        DomainObjectType.POST_ORDER: 'site_id',
        DomainObjectType.SITE_ASSET: 'site_id',
    }
    if object_type == DomainObjectType.COMPANY_POLICY:
        return source.organisation_id
    attribute = attribute_by_type.get(object_type)
    if attribute:
        related_id = getattr(source, attribute, None)
        if related_id is not None:
            return related_id
    return source.id
