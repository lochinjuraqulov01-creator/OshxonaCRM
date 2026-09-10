"""config/exceptions.py — yagona xato javoblari (API kontrakti barqarorligi uchun)."""
import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('apps')


class SmartOshxonaAPIException(exceptions.APIException):
    """Proyekt bo'ylab ishlatiladigan maxsus API istisnosi."""

    def __init__(self, message: str, code: str = 'error', status_code: int = 400):
        self.detail = {'message': message, 'code': code}
        self.status_code = status_code
        super().__init__(self.detail)


def custom_exception_handler(exc, context):
    """Barcha xatolarni yagona formatda qaytaradi:
    { "success": false, "error": {...}, "message": "..." }
    """
    response = exception_handler(exc, context)

    if response is None:
        if isinstance(exc, Http404):
            return Response(
                {'success': False, 'message': 'Topilmadi.'},
                status=status.HTTP_404_NOT_FOUND)
        if isinstance(exc, PermissionDenied):
            return Response(
                {'success': False, 'message': 'Ruxsat yo‘q.'},
                status=status.HTTP_403_FORBIDDEN)
        # Kutilmagan xato — log va umumiy javob
        logger.exception('Kutilmagan xato: %s', exc)
        return Response(
            {'success': False, 'message': 'Server xatosi. Keyinroq urinib ko‘ring.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    detail = response.data
    message = 'Xatolik yuz berdi.'
    if isinstance(detail, dict):
        first_key = next(iter(detail), None)
        val = detail.get(first_key)
        if isinstance(val, (list, tuple)) and val:
            message = str(val[0])
        elif isinstance(val, str):
            message = val
    elif isinstance(detail, (list, tuple)) and detail:
        message = str(detail[0])

    response.data = {
        'success': False,
        'message': message,
        'error': detail,
    }
    return response
