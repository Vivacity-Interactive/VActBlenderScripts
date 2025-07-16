import bpy

class _Settings:
    def __init__(self):
        self.b_negate = False
        self.b_data_name = True
        self.b_exclude_geometry_modifiers = True
        self.exclude_contains = ["_Floor_", "_Terrace_", "_Cornice_", "_Plinth_", "_Roof_", "_Passage_"]
        self.exclude_geometry_modifiers_contains = ["MA_","_Books", "_Scrolls", "_Leaves"]


class VActFilterSelection:
    def do_execute(self, context, settings):
        for item in context:
            _name = item.data.name if item.data and settings.b_data_name else item.name
            b_deselect = any(x in _name for x in settings.exclude_contains)
            b_modifiers = settings.b_exclude_geometry_modifiers and len(settings.exclude_geometry_modifiers_contains) > 0
            if b_modifiers:
                for modifier in item.modifiers:
                    if modifier.type in {'NODES'} and modifier.node_group:
                        b_deselect = b_deselect or any(x in modifier.node_group.name for x in settings.exclude_geometry_modifiers_contains) 
            if settings.b_negate: b_deselect = not b_deselect
            item.select_set(not b_deselect)


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActFilterSelection()
operator.do_execute(selection, settings)