import bpy, re

class _Settings:
    def __init__(self):
        self.b_rename_data = True
        self.regex_rename = "([0-9a-zA-Z_]+)(\.[0-9]+)?"
        self.regex_group = (1,)
        self.rename = "$1"


class VActSimpleRename:
    def do_execute(self, context, settings):
        _regx = re.compile(settings.regex_rename)
        for item in context:
            _context = item.data if settings.b_rename_data else item
            if not _context: continue
            _match = _regx.match(_context.name)
            _name = settings.rename
            for _group in settings.regex_group:
                _var = f"${_group}"
                _name = _name.replace(_var,_match.group(_group))
            #print((name, _name))
            _context.name = _name


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActSimpleRename()
operator.do_execute(selection, settings)