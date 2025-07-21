import bpy, re

def _resolve_collection(object, default):
    for collection in bpy.data.collections:
        if object.name in collection.objects: return collection
    return default

class _Settings:
    def __init__(self):
        self.modifier_match = "GNX_LODx"
        self.extract_lod = 0
        self.b_delete_original = True
        #self.b_hide_original = False
        self.b_extract_all_into_empty = False
        self.regex_replace = "GX_([0-9a-zA-Z_]+)_LOD[0-9]+"
        self.regex_group = (1)
        self.new_name = "SM_%X%"
        self.slot_match = "LOD"
        self.expand_into = "_Expanded"
        self.b_into_same_collection = True


class VActExpandGeometryLODName:
    def do_expand_lod(self, context, item, into, naming, settings):
        _lod_match =  settings.slot_match if settings.b_extract_all_into_empty else f"{settings.slot_match}{settings.extract_lod}"
        _empty = None
        b_has = False
        
        if settings.b_extract_all_into_empty:
            _match = naming.match(item.name)
            _empty = bpy.data.objects.new(settings.new_name.replace("%X%", _match.group(1)), None)
            into.objects.link(_empty)
            
        for slot in context.node_group.interface.items_tree:
            b_lod = slot.socket_type in {'NodeSocketObject'} and _lod_match in slot.name
            if b_lod:
                b_has = True
                object = context[slot.identifier]
                _object = bpy.data.objects.new(object.name, object.data)
                print((slot.socket_type, _lod_match,  object.name, object.data.name))
                if settings.b_extract_all_into_empty: _object.parent = _empty
                else: _object.matrix_world = item.matrix_world
                into.objects.link(_object)
                
        if b_has and settings.b_extract_all_into_empty: _empty.matrix_world = item.matrix_world
                 
        #if settings.b_hide_original:      
        if b_has and settings.b_delete_original: bpy.data.objects.remove(item)
        
                
        
    def do_execute(self, context, settings):
        _naming = re.compile(settings.regex_replace)
        _into = into = bpy.data.collections[settings.expand_into] if settings.expand_into else bpy.context.scene.collection
        
        for item in context:
            if not item.type in {"MESH"}: continue
            for modifier in item.modifiers:
                if modifier.type in {'NODES'} and modifier.node_group and settings.modifier_match in modifier.node_group.name:
                    if settings.b_into_same_collection: _into = _resolve_collection(item, into)
                    self.do_expand_lod(modifier, item, _into, _naming, settings)
                    break
                    

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActExpandGeometryLODName()
operator.do_execute(selection, settings)