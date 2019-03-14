from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter()
def tooltip(value):
    value = escape(value)
    return mark_safe('<i class="fa fa-question-circle tooltip-container">'
                     '<span class="tooltiptext">' + value + '</span></i>')