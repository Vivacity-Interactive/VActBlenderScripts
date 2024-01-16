import bpy, re, os, mathutils
#from array import array

class _Settings:
    def __init__(self):
        self.into = "_Frames"
        self.directory = "_in\\S6_T103_15_16_17_39_Export_06_12_15_02_17_eight_short\\"
        self.filter_regex = '.*\.obj'
        self.order_regex = '(.*)\.obj'
        self.order_group = 1
        self.frame_regex = None
        self.frame_group = 1
        self.fps = bpy.context.scene.render.fps
        self.frame_start = bpy.context.scene.frame_start
        self.frame_end = bpy.context.scene.frame_end
        self.use_shader_deform = False
        self.save_every = -1
        self.force_file_type = 'obj'
        self.wrap_empty = False
        self.range_frames = False
        
class VActImportSequence:
    class FileEntry:
        def __init__(self, path):
            self.path = path
            self.file = os.path.basename(path)
            _tpl = os.path.splitext(self.file)
            self.name = _tpl[0]
            self.ext = _tpl[1]
            self.objects = []
            self.frame = 0
            self.alpha = 1
            
    def _ensure_collection(self, name, context, settings):
        stack = [ x for x in bpy.data.collections ]
        
        while len(stack):
            collection = stack.pop()
            if collection.name == name: return collection
            for child in collection.children: stack.append(child)
        
        collection = bpy.data.collections.new(name)
        context.collection.children.link(collection)
        return collection
    
    def _order_files(self, context, settings):
        fx_by = lambda x : re.search(settings.order_regex, x.file).groups(settings.order_group)
        context.sort(key=fx_by)
        return context
    
    def _read_files(self, context, settings):
        _directory = os.path.join(os.path.dirname(bpy.data.filepath), settings.directory)
        _files = os.listdir(_directory)
        
        _entries = []
        for file in _files:
            _entries.append(VActImportSequence.FileEntry(os.path.join(_directory,file)))
        
        fx_check = lambda x : re.match(settings.filter_regex, x.file)
        return filter(fx_check, _entries) if settings.filter_regex else _entries
    
    def _animate_visibility(self, frame, index, alpha, context, settings):
        for object in context:
            object.animation_data_clear()
            
            object.hide_render = True
            object.hide_viewport = True
            object.keyframe_insert(data_path="hide_viewport", frame=settings.frame_start-1)
            object.keyframe_insert(data_path="hide_render", frame=settings.frame_start-1)
            object.hide_render = False
            object.hide_viewport = False
            object.keyframe_insert(data_path="hide_viewport", frame=frame)
            object.keyframe_insert(data_path="hide_render", frame=frame)
            object.hide_render = True
            object.hide_viewport = True
            object.keyframe_insert(data_path="hide_viewport", frame=frame+1)
            object.keyframe_insert(data_path="hide_render", frame=frame+1)
        
    
    def do_execute(self, context, settings):
        into = self._ensure_collection(settings.into, bpy.context.scene, settings) if settings.into else bpy.context.scene.collection        
        entries = self._read_files(context, settings)
        
        if (settings.frame_regex): self._order_files(files, settings)
        
        alpha = settings.fps / bpy.context.scene.render.fps
        
        index = 0
        for entry in entries:
            # not all file extensions mach the importer, so we need to construct a mapper and feed to filter_glob
            # select into collection
            
            #settings.force_file_type if settings.force_file_type else entry.ext
            bpy.ops.import_scene.obj(filepath=entry.path)
            
            entry.frame = (float(re.search(settings.frame_regex, entry.file).group(settings.frame_group)) if settings.frame_regex else index) * alpha
            entry.alpha = alpha
            _empty = None
            
            if settings.wrap_empty:
                    _empty = bpy.data.objects.new(entry.name, None)
                    into.objects.link(_empty)
                    entry.objects = [_empty]
                    
            for object in bpy.context.selected_objects:
                if settings.wrap_empty:
                    object.parent = _empty
                else:
                    entry.objects.append(object)
                    into.objects.link(object)
            
            self._animate_visibility(entry.frame, index, entry.alpha, entry.objects, settings)
            index += 1
        
        #fx_frame = lambda x: x.frame
        #entries.sort(key=fx_frame)
        
        #index = 0
        #for entry in entries:
        #    self._animate_visibility(entry, index, settings)
        #    index += 1
                
            
            
            


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActImportSequence()
operator.do_execute(selection, settings)