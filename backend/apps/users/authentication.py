"""apps/users/authentication.py — QO'SHIMCHA autentifikatsiya klasslari.

Oddiy JWTAuthentication faqat `Authorization` sarlavhasini o'qiydi.
Lekin brauzerdagi <img src="..."> va <a download> teglari sarlavha
yubora olmaydi (masalan: Admin panelda QR kod rasmlari).
Shuning uchun JWT ni `?token=` query paramidan ham o'qiydigan klass.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTQueryParamAuthentication(JWTAuthentication):
    """JWT: `Authorization` sarlavhasidan YOKI `?token=` paramidan.

    Ishlatilishi (faqat maxsus action'larda):
        @action(..., authentication_classes=[JWTQueryParamAuthentication])
    """

    def authenticate(self, request):
        # 1) Oddiy yo'l: Authorization sarlavhasi bo'lsa — standart oqim
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        # 2) Sarlavha yo'q → query paramdan o'qish (<img>/<a> uchun)
        raw_token = request.query_params.get('token')
        if not raw_token:
            return None  # hech qanday ma'lumot yo'q — anonim (permission hal qiladi)

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
