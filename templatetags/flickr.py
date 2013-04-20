from django import template
from django.core.urlresolvers import resolve

register = template.Library()

@register.tag(name="ifurl")
def do_ifurl(parser, token):
    try:
        tag_name, name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires one argument" % token.contents.split()[0])
    if not (name[0] == name[-1] and name[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)

    nodelist = parser.parse(('endifurl',))
    parser.delete_first_token()
    return IfUrlNode(name[1:-1], nodelist)

class IfUrlNode(template.Node):
    def __init__(self, name, nodelist):
        self.name = name
        self.nodelist = nodelist

    def render(self, context):
        path = context["request"].path
        match = resolve(path)
        if match.url_name == self.name:
            return self.nodelist.render(context)
        else:
            return ''
