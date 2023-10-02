"""
Notification filters
"""

from django.utils import timezone

from common.djangoapps.course_modes.models import CourseMode
from common.djangoapps.student.models import CourseEnrollment
from openedx.core.djangoapps.course_date_signals.utils import get_expected_duration
from openedx.core.djangoapps.notifications.base_notification import COURSE_NOTIFICATION_TYPES
from openedx.features.course_duration_limits.models import CourseDurationLimitConfig


class NotificationFilter:
    """
    Filter notifications based on their type
    """

    @staticmethod
    def filter_audit_expired(user_ids, course) -> list:
        """
        Check if the user has access to the course
        """
        verified_mode = CourseMode.verified_mode_for_course(course=course, include_expired=True)
        access_duration = get_expected_duration(course.id)
        course_time_limit = CourseDurationLimitConfig.current(course_key=course.id)
        if not verified_mode:
            return user_ids
        enrollments = CourseEnrollment.objects.filter(
            user_id__in=user_ids,
            course_id=course.id,
            mode=CourseMode.AUDIT,
        )
        if course_time_limit.enabled_for_course(course.id):
            enrollments = enrollments.filter(created__gte=course_time_limit.enabled_as_of)

        for enrollment in enrollments:
            content_availability_date = max(enrollment.created, course.start)
            expiration_date = content_availability_date + access_duration
            if expiration_date and timezone.now() > expiration_date:
                user_ids.remove(enrollment.user_id)

        return user_ids

    def apply_filters(self, user_ids, course, notification_type) -> list:
        """
        Apply all the filters
        """
        applicable_filters = COURSE_NOTIFICATION_TYPES.get(notification_type, [])
        for filter_name in applicable_filters:
            user_ids = getattr(self, filter_name)(user_ids, course)
        return user_ids
