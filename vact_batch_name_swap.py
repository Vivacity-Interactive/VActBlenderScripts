import bpy, re, uuid

class _Settings:
    def __init__(self):
        self.batch_swap = [
            (r'(SM_|UCX_)Mossy_Forest_Boulder_01_LOD(\d*)', r'\1Mossy_Forest_Boulder_02_LOD\2'),
        ]
        self.from_collection = None
        self.force_data_name = True


class VActBatchNameSwap:
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
        _tmp_name = str(uuid.uuid4())
        for pair in settings.batch_swap:
            _regex = re.compile(pair[0])
            for item in items:
                _match = _regex.match(item.name)
                if _match:
                    _name = item.name
                    name = _regex.sub(pair[1], _name)
                    other = bpy.data.objects.get(name)
                    if not other: continue
                    item.name = _tmp_name
                    other.name = _name
                    item.name = name
                    if settings.force_data_name:                    
                        if item.data:
                            item.data.name = _tmp_name
                            if other.data:
                                other.data.name = _name
                            item.data.name = name

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActBatchNameSwap()
operator.do_execute(selection, settings)