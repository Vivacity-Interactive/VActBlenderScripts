import bpy, re, mathutils, math

class _Settings:
    def __init__(self):
        self.face_names = ["left", "right", "up", "down", "front", "back"]
        self.face_look_ats = [
            mathutils.Vector(( 1,0,0)),
            mathutils.Vector((-1,0,0)),
            mathutils.Vector((0, 1,0)),
            mathutils.Vector((0,-1,0)),
            mathutils.Vector((0,0, 1)),
            mathutils.Vector((0,0,-1)),
        ]
        self.forward = "Y"
        self.up = "-Z"
        self.face_fov = 90
        self.suffix_regex = '^(\w|\d)'
        self.suffix_replace = "_CUBEMAP_%Y%_%X%"
        self.suffix_group = 1
        self.suffix_upper = True
        self.name = "AmbientExperience"
        self.camera_name_replace = "Camera%X%" #"Camera_CUBEMAP_%Y%_%X%"
        self.camera_sensor = 36
        self.use_hotspot_name = True
        self.collection = ""
        self.use_dof = True
        self.dof_distance = 3
        self.dof_f = 1.2
        self.dof_blades = 9
        self.dof_rotation = 120
        self.dof_ratio = 2.35
        self.hotspots_prefix = "HS_*"
        self.allow_hotspot_dublicate = False
        self.camera_collection = "_CubemapCameras"
        self.hotspot_collection = "Hotspots"


class VActCubmapSetup:
    def _ensure_collection(self, name, context, settings):
        stack = [ x for x in bpy.data.collections ]
        
        while len(stack):
            collection = stack.pop()
            if collection.name == name: return collection
            for child in collection.children: stack.append(child)
        
        collection = bpy.data.collections.new(name)
        context.collection.children.link(collection)
        return collection
    
    def _ensure_hotspot(self, hotspot, context, settings):
        b_hotspot = hotspot and settings.hotspots_prefix in hotspot.name
        
        if b_hotspot: return hotspot
    
        name = settings.hotspots_prefix + settings.name
        hotspot = bpy.data.objects.get(name)
        if settings.allow_hotspot_dublicate or not hotspot:
            hotspot = bpy.data.objects.new(name, None)
            context.objects.link(hotspot)
                   
        return hotspot
    
    def do_execute(self, context, settings):
        render = context.render
        render.views_format = 'MULTIVIEW'
        camera_into = self._ensure_collection(settings.camera_collection, context, settings) if settings.camera_collection else bpy.data.collections
        hotspot_into = self._ensure_collection(settings.hotspot_collection, context, settings) if settings.hotspot_collection else bpy.data.collections
        
        old_selection = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_pattern(pattern=settings.hotspots_prefix + "*")
        selection = bpy.context.selected_objects
        
        for hotspot in bpy.context.selected_objects:
            look_ats_len = len(settings.face_look_ats)
            
            for index, face_name in enumerate(settings.face_names):
                view_name = face_name + "_" + hotspot.name.lower()
                view = render.views.get(view_name)
                
                if not view:
                    view = render.views.new(view_name)
                
                _suffix_view = re.search(settings.suffix_regex, face_name).group(settings.suffix_group)
                
                if settings.suffix_upper:
                    _suffix_view = _suffix_view.upper()
                
                hotspot_name = hotspot.name if hotspot and settings.use_hotspot_name else settings.name
                _suffix =  settings.suffix_replace.replace("%X%",_suffix_view).replace("%Y%", hotspot_name)
                camera_name = settings.camera_name_replace.replace("%X%",_suffix)
                
                view.camera_suffix = _suffix
                
                camera = bpy.data.objects.get(camera_name)
                
                if not camera:
                    _camera_name = settings.camera_name_replace.replace(settings.suffix_replace,"").replace("%Y%", hotspot_name)
                    _camera = bpy.data.cameras.get(_camera_name)
                    
                    if not _camera:
                        _camera = bpy.data.cameras.new(name=_camera_name)
                    
                    camera = bpy.data.objects.new(camera_name, _camera)
                    camera_into.objects.link(camera)
                
                camera.data.lens_unit = 'FOV'
                camera.data.angle = round(math.radians(settings.face_fov))
                camera.data.sensor_width = settings.camera_sensor
                
                look_at = settings.face_look_ats[index % look_ats_len]
                
                camera.rotation_mode = 'QUATERNION'
                camera.rotation_quaternion = look_at.to_track_quat(settings.up,settings.forward)
                
                if settings.use_dof:
                    camera.data.dof.use_dof = True
                    camera.data.dof.focus_distance = settings.dof_distance
                    camera.data.dof.aperture_fstop = settings.dof_f
                    camera.data.dof.aperture_blades = settings.dof_blades
                    camera.data.dof.aperture_rotation = settings.dof_rotation
                    camera.data.dof.aperture_ratio = settings.dof_ratio
                
                camera.parent = hotspot
        
        bpy.ops.object.select_all(action='DESELECT')
        for object in old_selection: object.select_set(state=True)


operation = VActCubmapSetup()
operation.do_execute(bpy.context.scene, _Settings())