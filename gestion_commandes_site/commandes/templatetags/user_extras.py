from django import template

register = template.Library()


@register.filter(name='has_attr')
def has_attr(obj, attr_name):
    """Return True if object has attribute `attr_name`, otherwise False.

    Use in templates like: `{% if user|has_attr:'fournisseur_profile' %}`
    """
    try:
        return hasattr(obj, attr_name)
    except Exception:
        return False
