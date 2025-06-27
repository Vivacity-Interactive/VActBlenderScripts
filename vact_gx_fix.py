import bpy

class _Settings:
    def __init__(self):
        self.fix = 'GX_'
        self.target = 'SM_'
        self.b_remove = True
        self.b_fix_filter = True
        self.node_groups_remove = {'GN_Single'}
        self.node_groups_fix = {'GN_Array', 'GN_Mirror', 'GN_Path'}
        self.b_restore = False

class VActGXFix:
    def do_execute(self, context, settings):
        b_remove = settings.b_remove and len(settings.node_groups_remove) > 0
        b_filter = settings.b_fix_filter and len(settings.node_groups_fix) > 0
        
        if not settings.b_restore:
            for item in context:
                b_fix = len(item.modifiers) > 0
                b_check = (b_filter or b_remove) and b_fix
                if b_check:
                    b_fix = b_fix and not b_filter
                    for modifier in item.modifiers[:]:
                        if modifier.type in {'NODES'} and modifier.node_group:
                            b_fix = b_fix or (not b_filter) or (modifier.node_group.name in settings.node_groups_fix)
                            if b_remove and modifier.node_group.name in settings.node_groups_remove: item.modifiers.remove(modifier)
                
                if b_fix: item.name = item.name.replace(settings.target, settings.fix)
        else:
            for item in context: item.name = item.name.replace(settings.fix, settings.target)


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActGXFix()
operator.do_execute(selection, settings)