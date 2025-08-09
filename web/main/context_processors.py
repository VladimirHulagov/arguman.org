from django.conf import settings

EXPORT_SETTINGS = [
    "BASE_DOMAIN",
]

export_settings_vars = dict()
for settings_key in EXPORT_SETTINGS:
    value = getattr(settings, settings_key, None)
    if not value:
        continue
    export_settings_vars[settings_key] = value


def settings(request):
    return {"settings": export_settings_vars}
