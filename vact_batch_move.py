import bpy, re

class _Settings:
    def __init__(self):
        self.batch_move = [
            (r'SM_.*_LOD0', "Decor"),
            (r'UCX_.*', "UCX"),
            (r'SM_.*_LOD[1-9]\d*', "LOD"),
        ]
        self.force_collection = True
        self.from_collection = '_Import'
        self.strict_move = True


class VActBatchMove:
    def _ensure_collection(self, name, settings):
        _stack = [ x for x in bpy.data.collections ]
        while len(_stack):
            into = _stack.pop()
            if into.name == name: return into
            for child in into.children: _stack.append(child)
        
        into = None
        if settings.force_collection:
            into = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(into)
        return into
        
    def do_execute(self, context, settings):
        _collection = bpy.data.collections.get(settings.from_collection) if settings.from_collection else None
        items = _collection.objects if _collection else bpy.data.objects
        for pair in settings.batch_move:
            _regex = re.compile(pair[0])
            _into = self._ensure_collection(pair[1], settings)
            if not _into: continue 
            
            for item in items:
                _match = _regex.match(item.name)
                if _match:
                    if settings.strict_move:
                        _into.objects.link(item)
                    


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActBatchMove()
operator.do_execute(selection, settings)