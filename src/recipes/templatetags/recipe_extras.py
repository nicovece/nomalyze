from django import template

from widget_tweaks.templatetags.widget_tweaks import add_class

register = template.Library()


@register.simple_tag(takes_context=True)
def is_hero_page(context):
    """
    Check if the current page is a hero page (home, login, logout).
    Returns True if the current URL name is one of the hero pages.
    """
    request = context["request"]
    hero_pages = ["home", "login", "logout"]
    return request.resolver_match.url_name in hero_pages


@register.simple_tag(takes_context=True)
def get_nav_classes(context, hero_class, default_class):
    """
    Return the appropriate CSS classes based on whether it's a hero page.
    """
    if is_hero_page(context):
        return hero_class
    return default_class


@register.simple_tag(takes_context=True)
def get_footer_classes(context):
    """
    Return the appropriate footer CSS classes based on whether it's a hero page.
    """
    if is_hero_page(context):
        return "fixed right-0 z-50 bottom-0 left-0 bg-alternate_a-800/70 backdrop-blur-sm text-accent-300"
    return "bg-alternate_a-100 border-t border-gray-200 text-accent-800"


@register.simple_tag
def search_tip_classes():
    return "max-w-max border-b border-dashed border-[currentColor]/75 pb-3"


@register.filter
def split(value, delimiter=","):
    """Split a string by delimiter and return a list"""
    return [item.strip() for item in value.split(delimiter) if item.strip()]


@register.filter
def tailwind_input(field):
    """
    Apply Tailwind CSS classes to form fields.
    Works with TextInput, NumberInput, Select, and other widget types.
    """
    classes = "w-full px-3 py-2 border border-accent-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-accent-100 focus:border-accent-300 transition-colors duration-200 text-accent-600"
    return add_class(field, classes)


@register.filter
def tailwind_select(field):
    """
    Apply Tailwind CSS classes specifically for Select fields.
    This ensures proper styling for dropdown menus.
    """
    classes = "w-full px-3 py-2 border border-accent-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-accent-100 focus:border-accent-300 transition-colors duration-200 text-accent-600 bg-white"
    return add_class(field, classes)


@register.filter
def media_to_static(image_path):
    """
    Convert media URL to static URL for recipe images.
    Extracts filename from media path and returns static path.
    Example: 'recipes/image.jpg' -> 'images/recipes/image.jpg'
    """
    from django.templatetags.static import static

    if not image_path:
        return static("images/no_picture.png")
    # Extract just the filename portion (e.g., 'recipes/image.jpg')
    path_str = str(image_path)
    # If it's already a full URL or starts with /, return as is
    if path_str.startswith("http") or path_str.startswith("/static"):
        return path_str
    # Convert media path to static path
    # 'recipes/image.jpg' -> 'images/recipes/image.jpg'
    return static(f"images/{path_str}")
