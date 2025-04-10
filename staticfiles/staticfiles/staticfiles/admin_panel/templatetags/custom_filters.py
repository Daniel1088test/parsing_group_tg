from django import template

register = template.Library()

@register.filter
def filter_by_category(messages, category_id):
    return [msg for msg in messages if msg.channel.category.id == category_id]