bl_info = {
    "name": "MDVisual",
    "author": "Randy Wind",
    "version": (0, 7, 3),
    "blender": (4, 0, 0),
    "python" : (3, 1, 0),
    "location": "Scene > MDVisual",
    "description": "Load molecular dynamics trajectory spans into blender",
    "warning": "Dependency automatic pip package dependency on MDAnalysis",
    "doc_url": "",
    "support" : "TESTING",
    "category": "Import-Export"
}


_mdvisual = {
    "ready": False,
    "exceptions": [],
    "trace": [],
    "deps" : [
        "pip",
        "MDAnalysis"
    ],
    "assert_deps" : [
        "MDAnalysis",
        "numpy"
    ],
    "pkg_dir": "python_lib",
    "python_lib": None
}

import bpy, sys, math, mathutils, bmesh

from bpy.props import (
    IntProperty, 
    BoolProperty, 
    EnumProperty, 
    StringProperty, 
    PointerProperty, 
    FloatProperty, 
    CollectionProperty, 
    BoolProperty, 
    FloatVectorProperty
)

from bpy.types import (
    Operator, 
    PropertyGroup, 
    Panel, 
    ParticleSettings, 
    Mesh, 
    Object, 
    UIList, 
    ID, 
    Menu
)

from mathutils import (
    Vector, 
    Quaternion, 
    Matrix
)

class _MDImport:
    @classmethod
    def module(cls, name):
        import importlib
        _module = importlib.import_module(name)
        if not _module: raise ModuleNotFoundError()
        return _module

class MDVisual:
    @classmethod
    def cache(cls, context=None):
        range = cls.range(context)
        return range.md_cache
    
    @classmethod
    def context(cls, context=None):
        return context.scene.md_instance if context else bpy.context.scene.md_instance
    
    @classmethod
    def context_poll(cls, context=None):
        return bool(bpy.context.scene.md_instance)
    
    @classmethod
    def system(cls, context=None):
        return context.scene.md_system if context else bpy.context.scene.md_system

    @classmethod
    def system_poll(cls, context=None):
        return bool(context.scene.md_system)

    @classmethod
    def range(cls, context=None):
        system = cls.system(context)
        return system.md_ranges[system.md_ranges_index]

    @classmethod
    def range_add(cls, context=None):
        system = cls.system(context)
        return system.md_ranges.add()
    
    @classmethod
    def range_remove(cls, context=None, target=None):
        system = cls.system(context)
        system.md_ranges.remove(system.md_ranges_index)
        system.md_ranges_index -= 1

    @classmethod
    def range_poll(cls, context=None):
        system = cls.system(context)
        return bool(system) and bool(system.md_ranges) and system.md_ranges_index < len(system.md_ranges)


class MDParticle:
    location = Vector()
    rotation = Quaternion()
    velocity = Vector()
    name = ""
    id = 0
    type = None


class MDFrame:    
    id = 0
    data = None
    
    def particles(self):
        context = MDVisual.context()
        for atom in context.atoms:
            yield self.get(atom.ix)
        
    def get(self, id):
        context = MDVisual.context()
        particle = MDParticle()
        particle.location = self.data.positions[id]
        #particle.velocity = self.data.velocities[id]
        particle.name = context.atoms.names[id]
        particle.type = context.atoms.types[id]
        particle.id = id
        return particle
    
    def __iter__(self):
        return self.particles()


class MDInstance:
    def init(self, file_topology, file_trajectory):
        scene = bpy.types.Scene
        if not file_topology or not file_trajectory:
            return False
        
        try:
            MDAnalysis = _MDImport.module("MDAnalysis")
            
            universe = MDAnalysis.Universe(file_topology, file_trajectory)
            #universe = self.Imports.MDAnalysis.Universe(file_topology, file_trajectory)
            
            if not scene.md_instance is None:
                del scene.md_instance
            scene.md_instance = universe
            if scene.md_instance is None:
                raise TypeError()
        except Exception as ex:
            scene.md_exception = ex
            print(ex)
            return False
        
        return True
    
    def context(self):
        return MDVisual.context()
    
    def entities(self):
        numpy = _MDImport.module("numpy")

        context = self.context()
        if not context:
            return None

        for type in numpy.unique(context.atoms.types):
            yield type
    
    def frame(self, frame_at):
        context = self.context()
        if not context:
            return None
        
        frame = MDFrame()
        frame.data = context.trajectory[frame_at]
        return frame
    
    def trajectory(self, frame_from, frame_to, frame_step=1):
        context = self.context()
        if not context:
            return None
        
        for step in context.trajectory[frame_from:frame_to:frame_step]:
            frame = MDFrame()
            frame.id = step.frame
            frame.data = step
            yield frame
    
    def frame_max(self):
        context = self.context()
        if not context:
            return 0
        
        return len(context.trajectory)
        
    def frame_min(self):
        return 0

    def particle_count(self):
        context = self.context()
        if not context:
            return 0
        
        return len(context.atoms)
    
    def composition_count(self):
        context = self.context()
        if not context:
            return 0
        
        return len(context.residues)

    def segment_count(self):
        context = self.context()
        if not context:
            return 0
        
        return len(context.segments)
    
    def ready(self):
        return bool(self.context()) and (self.frame_max() > 0)
    
    def changed(self):
        return bpy.context.scene.md_changed


class MDEntity(PropertyGroup):
    def get_count(self):
        return self.get('md_count', 0)

    md_count : IntProperty(name="Count", min=0, default=0, get=get_count)
    md_enabled : BoolProperty(name="Enabled")


class MDCache(PropertyGroup):
    md_id : IntProperty(name="Particle Id", min=0, default=0)
    md_view : PointerProperty(name="View", type=Object)
    md_view_id : IntProperty(name="View Id", min=0, default=0)


class MDRange(PropertyGroup):
    def set_frame_start(self, value):
        system = MDVisual.system()
        if value >= system.md_frame_min and value <= system.md_frame_max:
            self['md_frame_start'] = value
            self['md_frame_end'] = max(value, self.md_frame_end)
        else:
            self['md_frame_start'] = max(system.md_frame_min, min(value, system.md_frame_max))
    
    def set_frame_end(self, value):
        system = MDVisual.system()
        if value >= system.md_frame_min and value <= system.md_frame_max:
            self['md_frame_end'] = value
            self['md_frame_start'] = min(value, self.md_frame_start)
        else:
            self['md_frame_end'] = min(system.md_frame_max, max(value, system.md_frame_min))
    
    def set_frame_scene_start(self, value):
        self['md_frame_scene_start'] = value
        self['md_frame_scene_end'] = max(value, self.md_frame_scene_end)
    
    def set_frame_scene_end(self, value):
        self['md_frame_scene_end'] = value
        self['md_frame_scene_start'] = min(value, self.md_frame_scene_start)  
    
    def get_frame_start(self):
        return self.get('md_frame_start', 0)
    
    def get_frame_end(self):
        return self.get('md_frame_end', 0)
    
    def get_frame_scene_start(self):
        return self.get('md_frame_scene_start', bpy.context.scene.frame_start)
    
    def get_frame_scene_end(self):
        return self.get('md_frame_scene_end', bpy.context.scene.frame_end)
    
    def get_frame_count(self):
        return int((self.md_frame_end - self.md_frame_start) / self.md_frame_step)

    def get_ready(self):
        return bool(len(self.md_cache))
    
    def update(self):
        self.md_frame_start = self.md_frame_start
        self.md_frame_end = self.md_frame_end
        self.md_frame_start = self.md_frame_start
    
    md_icon : StringProperty(name="Icon", default='PARTICLE_PATH')
    md_frame_start : IntProperty(name="MD Start", min=0, options={'LIBRARY_EDITABLE'}, set=set_frame_start, get=get_frame_start)
    md_frame_end : IntProperty(name="MD End", min=0, options={'LIBRARY_EDITABLE'}, set=set_frame_end, get=get_frame_end)
    md_frame_scene_start : IntProperty(name="Scene Start", soft_min=0, options={'LIBRARY_EDITABLE'}, set=set_frame_scene_start, get=get_frame_scene_start)
    md_frame_scene_end : IntProperty(name= "Scene End", soft_min=0, options={'LIBRARY_EDITABLE'}, set=set_frame_scene_end, get=get_frame_scene_end)
    md_frame_step : IntProperty(name= "MD Step", min=1, default = 1, options={'LIBRARY_EDITABLE'})
    md_frame_count : IntProperty(name= "MD Count", min=0, options={'LIBRARY_EDITABLE'}, get=get_frame_count)
    #md_mask_box_from : FloatVectorProperty(name="Mask From", subtype='COORDINATES', unit='NONE')
    #md_mask_box_to : FloatVectorProperty(name="Mask To", subtype='COORDINATES', unit='NONE')
    md_bind : PointerProperty(name="Bind Root", type=Object, options={'LIBRARY_EDITABLE'})
    md_ready : BoolProperty(name="Ready", options={'LIBRARY_EDITABLE'}, default=False, get=get_ready)
    md_changed : BoolProperty(name="Changed", options={'LIBRARY_EDITABLE'}, default=True)
    md_cache : CollectionProperty(name="Cache",type=MDCache)
    md_causality : FloatProperty(name="Animation Causality Limit", options={'LIBRARY_EDITABLE'}, default=float("inf"))


class MDSystem(PropertyGroup, MDInstance):
    def get_frame_min(self):
        return self.frame_min()
    
    def get_frame_max(self):
        return self.frame_max()
    
    def get_ready(self):
        return self.ready()

    def get_particle_count(self):
        return self.particle_count()
    
    def get_composition_count(self):
        return self.composition_count()
    
    def get_segment_count(self):
        return self.segment_count()
    
    def load(self):
        self.name = bpy.path.basename(self.md_topology)
        self.init(bpy.path.abspath(self.md_topology), bpy.path.abspath(self.md_trajectory))
        
        self.md_particle_entities.clear()
        
        for name in self.entities():
            entity = self.md_particle_entities.add()
            entity.name = name
        
        for range in self.md_ranges:
            range.update()
    
    md_frame_min : IntProperty(name="Min Frame", min=0, options={'LIBRARY_EDITABLE'}, get=get_frame_min)
    md_frame_max : IntProperty(name="Max Frame", min=0, options={'LIBRARY_EDITABLE'}, get=get_frame_max)
    md_topology : StringProperty(name="Topology", subtype='FILE_PATH')
    md_trajectory : StringProperty(name="Trajectory", subtype='FILE_PATH')
    md_ranges : CollectionProperty(name="Ranges",type=MDRange)
    md_particle_entities : CollectionProperty(name="Particle Entities",type=MDEntity)
    md_composition_entities : CollectionProperty(name="Composition Entities",type=MDEntity)
    md_segment_entities : CollectionProperty(name="Segments Entities",type=MDEntity)
    md_ranges_index : IntProperty(name="Range Index", min=0, default=0)
    md_particle_entities_index : IntProperty(name="Particle Entity Index", min=0, default=0)
    md_composition_entities_index : IntProperty(name="Composition Entity Index", min=0, default=0)
    md_segment_entities_index : IntProperty(name="Segment Entity Index", min=0, default=0)
    md_ready : BoolProperty(name="Ready", options={'LIBRARY_EDITABLE'}, get=get_ready)
    md_changed : BoolProperty(name="Changed", options={'LIBRARY_EDITABLE'}, default=True)
    md_particle_count : IntProperty(name="Particle Count", min=0, default=0, get=get_particle_count)
    md_composition_count : IntProperty(name="Composition Count", min=0, default=0, get=get_composition_count)
    md_segment_count : IntProperty(name="Segment Count", min=0, default=0, get=get_segment_count)
    md_dimension_lengths : FloatVectorProperty(name="Lengths", subtype='XYZ_LENGTH', unit='LENGTH')
    md_dimension_angles : FloatVectorProperty(name="Angles", subtype='AXISANGLE', unit='ROTATION')


class MDVisualHelper:
    def load_system(self, context):
        system = MDVisual.system(context)
        system.load()
        return system
    
    def add_range(self, context, post_fix=""):
        to_return = MDVisual.range_add(context)
        to_return.name = "MDRange" + post_fix
        return to_return
    
    def new_object(self, context, name, data=None, collection=None):
        to_return = bpy.data.objects.new(name, data)
        if collection:
            collection.objects.link(to_return)
        return to_return

    def new_collection(self, context, name=None, collection=None):
        name = "Collection" if not name else name
        collection = context.scene.collection if not collection else collection
        to_return = bpy.data.collections.new(name)
        if collection:
            collection.children.link(to_return)
        return to_return

    def new_empty(self, context, type=None, name=None, location=None, collection=None):
        name = "Empty" if not name else name
        type = 'PLAIN_AXES' if not type else type
        collection = context.scene.collection if not collection else collection 
        location = context.scene.cursor.location if not location else location
        to_return = self.new_object(context, name, None, collection)
        to_return.empty_display_type = type
        to_return.location = location
        return to_return

    def new_root(self, context, name="", collection=None):
        name = "Root" if not name else name
        to_return = self.new_empty(context, 'ARROWS', name, None, collection)
        return to_return

    def new_mask(self, context, parent, pre_fix="", location=None, collection=None):
        name = "Mask" if not pre_fix else "Mask." + pre_fix
        to_return = self.new_empty(context, 'CUBE', name, location, collection)
        to_return.parent = parent
        return to_return
    
    def new_bounds(self, context, parent, pre_fix="", location=None, collection=None):
        name = "Dimensions" if not pre_fix else "Dimensions." + pre_fix
        to_return = self.new_empty(context, 'CUBE', name, location, collection)
        to_return.parent = parent
        return to_return
    
    def target_frame(self, context, frame, item):
        duration = item.md_frame_end - item.md_frame_start
        duration_scene = item.md_frame_scene_end - item.md_frame_scene_start
        by_duration = 1.0 / duration
        target = item.md_frame_scene_start + (frame - item.md_frame_start) * by_duration * duration_scene
        return target


class MDVISUAL_InstanceHelper(MDVisualHelper):
    def new_cube_data(self, context):
        return (
            [(-1.0, -1.0, -1.0),(-1.0, -1.0, 1.0),(-1.0, 1.0, -1.0),(-1.0, 1.0, 1.0),(1.0, -1.0, -1.0),(1.0, -1.0, 1.0),(1.0, 1.0, -1.0),(1.0, 1.0, 1.0)],
            [(2, 0),(0, 1),(1, 3),(3, 2),(6, 2),(3, 7),(7, 6),(4, 6),(7, 5),(5, 4),(0, 4),(5, 1)],
            [(0, 1, 3, 2),(2, 3, 7, 6),(6, 7, 5, 4),(4, 5, 1, 0),(2, 6, 4, 0),(7, 3, 1, 5)]
        )
    
    def new_mesh(self, context, name=None, collection=None):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(*self.new_cube_data(context))
        mesh.update()
        to_return = self.new_object(context, name, mesh, collection)
        return to_return
    
    def new_entity(self, context, entity, collection=None, parent=None):
        name = "Entity" if not entity.name else entity.name
        to_return = self.new_mesh(context, name, collection)
        to_return.parent = parent
        return to_return

    def new_particle(self, context, to_clone, particle, parent, collection=None):
        name = "Particle" if not particle.name else particle.name + "." + str(particle.id)
        to_return = self.new_object(context, name, to_clone.data, collection)
        to_return.location = particle.location
        to_return.parent = parent   
        return to_return
    
    def built(self, context, item):
        system = MDVisual.system(context)
        collection = self.new_collection(context, item.name)
        item.md_cache.clear()
        
        root = self.new_root(context, item.name, collection)
        item.md_bind = context.scene.objects[root.name]
        
        particle_entities = self.new_collection(context, "_Entities." + root.name, collection)
        particles = self.new_collection(context, "_Particles." + root.name, collection)
        
        # Create Selected System Enity Meshes
        _types = {}
        for entity in system.md_particle_entities:
            if entity.md_enabled:
                _types[entity.name] = self.new_entity(context, entity, particle_entities)
        
        # Initialize First Frame Particle Instances
        _particles = []
        for particle in system.frame(item.md_frame_start):
            view_entity = _types.get(particle.type)
            if view_entity:
                view = self.new_particle(context, view_entity, particle, root, particles)
                entry = item.md_cache.add()
                entry.name = view.name
                entry.md_id = particle.id
                entry.md_view = context.scene.objects[view.name]
        
        root.select_set(True)
                
    def animate(self, context, item):
        system = MDVisual.system(context)
        causality = item.md_causality
        
        for entry in item.md_cache:
                entry.md_view.animation_data_clear()
        
        for frame in system.trajectory(item.md_frame_start, item.md_frame_end, item.md_frame_step):
            target =  self.target_frame(context, frame.id, item)
            for entry in item.md_cache:
                # TODO set interpolation of none causal translation
                # due to periodic bondaries to CONSTANT interpolation.
                location = frame.get(entry.md_id).location
                view = entry.md_view
                view.location = location
                view.keyframe_insert(data_path="location", frame=target)


class MDVISUAL_MeshHelper(MDVisualHelper):
    def built(self, context, item):
        # Create System Root Object
        
            # Create System Enity Meshes
                
                # (Optional) Create System Animation Library
                # (Optional) Create System Particle Animation
                # Create Vertex Key Frames Entities Meshes
            
        # Finalize and Register
        pass

class MDVISUAL_PointCloudHelper(MDVisualHelper):
    def built(self, context, item):
        # Create System Root Object
        
            # Create System Enity Point Clouds
                
                # Create Points Cloude
            
        # Finalize and Register
        pass

    
class MDVISUAL_ParticleSystemHelper(MDVisualHelper):
    def built(self, context, item):
        # Create System Root Object
        
            # Create Enity Volume Particle Systems.
            # Create Enity Volume Particle Systems Settings.
                
                # Create/Set Particle Dynamics Cash
        
        # Finalize and Register
        pass

    
class MDVISUAL_HairSystemHelper(MDVisualHelper):
    def built(self, context, item):
        # Create System Root Object
        
            # Create Enity Hair Particle Systems.
            # Create Enity Hair Particle Systems Settings.
                
                # Create/Set Particle Dynamics Cash
        
        # Finalize and Register
        pass  


class MDVISUAL_GeometricNodesHelper(MDVisualHelper):
    def built(self, context, item):
        pass  
    
    
class MDVISUAL_CurveHelper(MDVisualHelper):
    def built(self, context, item):
        pass  


class MDVISUAL_MetaballsHelper(MDVisualHelper):
    def built(self, context, item):
        pass


class MDSYSTEM_:
    @classmethod
    def poll(cls, context):
        return MDVisual.system(context)


class MRANGE_:
    @classmethod
    def poll(cls, context):
        return MDVisual().range_poll()

class MDRANGE_OT_Particle_System_New(MDSYSTEM_, MDVISUAL_ParticleSystemHelper, Operator):
    """Create MD System as Particle System"""
    bl_idname = "mdvisual.new_range_particle_system"
    bl_label = "As Particle System(s)"
    bl_icon = 'PARTICLES'

    def execute(self, context):
        range = self.add_range(context, "ParticleSystem")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Hair_System_New(MDSYSTEM_, MDVISUAL_HairSystemHelper, Operator):
    """Create MD System as Hair Particle System"""
    bl_idname = "mdvisual.new_range_hair_system"
    bl_label = "As Hair Particle System(s)"
    bl_icon = 'HAIR_DATA'

    def execute(self, context):
        range = self.add_range(context, "HairSystem")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Mesh_New(MDSYSTEM_, MDVISUAL_MeshHelper, Operator):
    """Create MD System as Mesh Vertices"""
    bl_idname = "mdvisual.new_range_mesh"
    bl_label = "As Mesh(s) Vertices"
    bl_icon = 'MESH_DATA'

    def execute(self, context):
        range = self.add_range(context, "Vertices")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Instance_New(MDSYSTEM_, MDVISUAL_InstanceHelper, Operator):
    """Create MD System as Object Instances"""
    bl_idname = "mdvisual.new_range_instance"
    bl_label = "As Object Instance(s)"
    bl_icon = 'OBJECT_DATA'

    def execute(self, context):
        range = self.add_range(context, "Instances")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Geometric_Nodes_New(MDSYSTEM_, MDVISUAL_GeometricNodesHelper, Operator):
    """Create MD System as Geometric Nodes"""
    bl_idname = "mdvisual.new_range_geometirc_nodes"
    bl_label = "As Geometric Nodes"
    bl_icon = 'NODETREE'

    def execute(self, context):
        range = self.add_range(context, "GeometricNodes")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}
    

class MDRANGE_OT_Curve_New(MDSYSTEM_, MDVISUAL_CurveHelper, Operator):
    """Create MD System as Curves"""
    bl_idname = "mdvisual.new_range_curve"
    bl_label = "As Curves"
    bl_icon = 'CURVE_DATA'

    def execute(self, context):
        range = self.add_range(context, "Curves")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Point_Cloud_New(MDSYSTEM_, MDVISUAL_PointCloudHelper, Operator):
    """Create MD System as Point Cloude"""
    bl_idname = "mdvisual.new_range_point_cloud"
    bl_label = "As Point Cloud(s)"
    bl_icon = 'POINTCLOUD_DATA'

    def execute(self, context):
        range = self.add_range(context, "PointCloud")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}
    

class MDRANGE_OT_Metaball_New(MDSYSTEM_, MDVISUAL_MetaballsHelper, Operator):
    """Create MD System as Metaball"""
    bl_idname = "mdvisual.new_range_metaball"
    bl_label = "As Metaball(s)"
    bl_icon = 'META_BALL'

    def execute(self, context):
        range = self.add_range(context, "Metaballs")
        range.md_icon = self.bl_icon
        self.built(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Refresh(MRANGE_, MDVISUAL_InstanceHelper, Operator):
    """Refresh MD Range"""
    bl_idname = "mdvisual.refresh_range"
    bl_label = "Refresh"

    def execute(self, context):
        range = MDVisual.range(context)
        self.animate(context, range)
        return {'FINISHED'}


class MDRANGE_OT_Delete(MRANGE_, MDVisualHelper, Operator):
    """Delete MD Range"""
    bl_idname = "mdvisual.delete_range"
    bl_label = "Delete"

    def execute(self, context):
        MDVisual.range_remove(context)
        return {'FINISHED'}


class MDSYSTEM_OT_Refresh(MDSYSTEM_, MDVisualHelper, Operator):
    """Refresh MD System"""
    bl_idname = "mdvisual.refresh_system"
    bl_label = "Refresh"
    
    @classmethod
    def poll(cls, context):
        system = MDVisual.system(context)
        return system and system.md_topology and system.md_trajectory

    def execute(self, context):
        self.load_system(context)
        return {'FINISHED'}
            

class MDRANGE_UL_List(UIList):
    """MDRange List"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        _icon = icon if item.md_icon is None else item.md_icon
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon = _icon)
        if self.layout_type in {'GRID'} :
            layout.alignment = 'CENTER'
            layout.label(text="", icon = _icon)


class MDENTITY_UL_List(UIList):
    """MDEntity List"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            col = layout.column()
            col.label(text=item.name)
            #col.label(text=item.md_count)
            col = layout.column()
            col.prop(item, "md_enabled", text="")
        if self.layout_type in {'GRID'} :
            layout.alignment = 'CENTER'
            col = layout.column()
            col.label(text=item.name[:3])
            col.prop(item, "md_enabled", text="")


class MDRANGE_MT_Add_Bind(Menu):
    """MDVisual Add Binds Menu"""
    bl_label = "Bind As"
    bl_idname = "MDRANGE_MT_Add_Bind"

    def draw(self, context):
        layout = self.layout
        layout.operator("mdvisual.new_range_instance", icon='OBJECT_DATA')
        layout.operator("mdvisual.new_range_mesh", icon='MESH_DATA')
        layout.operator("mdvisual.new_range_particle_system", icon='PARTICLES') 
        layout.operator("mdvisual.new_range_geometirc_nodes", icon='NODETREE')
        layout.operator("mdvisual.new_range_metaball", icon='META_BALL')
        layout.operator("mdvisual.new_range_point_cloud", icon='POINTCLOUD_DATA')
        layout.operator("mdvisual.new_range_hair_system", icon='HAIR_DATA')
        layout.operator("mdvisual.new_range_curve", icon='CURVE_DATA')


class MDVISUAL_PT:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {"DEFAULT_CLOSED"}


class MDVISUAL_PT_Main(MDVISUAL_PT, Panel):
    """MDVisual Control Panel"""
    bl_label = "Molecular Dynamics"
    bl_idname = "MDVISUAL_PT_Main"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        system = MDVisual.system(context)
        
        row = layout.row(align=True)
        sub = row.row()
        sub.prop(system,"name", text="MD System")
        sub.enabled = False
        row.alert = not system.md_ready
        row.operator("mdvisual.refresh_system", text="", icon='FILE_REFRESH')
        col = layout.column()
        col.prop(system,"md_topology")
        col.prop(system,"md_trajectory")
        col = layout.column(align=True)
        col.prop(system, "md_frame_min")
        col.prop(system, "md_frame_max")
        col.prop(system, "md_particle_count")
        col.prop(system, "md_composition_count")
        col.prop(system, "md_segment_count")
        
        #md_particle_entities
        #md_composition_entities
        #md_segment_entities
        col.template_list('MDENTITY_UL_List', "", system, "md_particle_entities", system, "md_particle_entities_index")
        
        row = layout.row()
        col = row.column()
        col.template_list('MDRANGE_UL_List', "", system, "md_ranges", system, "md_ranges_index")
        col = row.column(align=True)
        col.menu('MDRANGE_MT_Add_Bind', text='', icon='ADD')
        col.operator("mdvisual.delete_range", text="", icon='REMOVE')
        layout.separator()
        
        if MDVisual.range_poll(context):
            range = MDVisual.range(context)
            
            row = layout.row(align=True)
            col = row.column(align=True)
            col.prop(range,"name", text="MD Range")
            col = row.column(align=True)
            col.operator("mdvisual.refresh_range", text="", icon='ANIM')
            col.enabled = range.md_frame_count > 0 and system.md_ready
            row = layout.row()
            row.prop(range,"md_bind")
            row.enabled = False
            row = layout.row(align=True)
            
            col = row.column(align=True)
            col.alert = range.md_frame_count <= 0
            col.prop(range, "md_frame_start")
            col.prop(range, "md_frame_end")
            col.prop(range, "md_frame_step")
            col.prop(range, "md_frame_count")
 
            col = row.column(align=True)
            col.alert = range.md_frame_scene_start >= range.md_frame_scene_end
            col.prop(range, "md_frame_scene_start")
            col.prop(range, "md_frame_scene_end") 
            row = layout.row()
            row.prop(range, "md_causality") 
            #pow = layout.column(align=True)
            #col = pow.column(align=True)
            #row = col.row(align=True)
            #row.prop(range, "md_mask_box_from")
            #col = pow.column(align=True)
            #row = col.row(align=True)
            #row.prop(range, "md_mask_box_to")


#change to operation
def _mdvisual_setup():
    _mdvisual["ready"] = False
    try:
        for dep in _mdvisual["assert_deps"]:
            _MDImport.module(dep)

        _mdvisual["ready"] = True
    except Exception as ex0:
        _mdvisual["exceptions"] += [ex0]
        import sys
        import os
        import subprocess
        
        # Find python executable
        python_exe = sys.executable #os.path.join(sys.prefix, 'bin', 'python.exe')
        
        # Ensure user library path
        pkg_dir = _mdvisual["python_lib"]
        if (not pkg_dir) and _mdvisual["pkg_dir"]:
            plugin_dir = os.path.dirname(bpy.data.filepath) or os.getcwd()
            pkg_dir = _mdvisual["python_lib"] = os.path.join(plugin_dir, _mdvisual["pkg_dir"])
            os.makedirs(pkg_dir, exist_ok=True)
            if pkg_dir and pkg_dir not in sys.path: sys.path.insert(0, pkg_dir)
        
        _mdvisual["trace"] += [subprocess.run([python_exe, "-m", "ensurepip"])]
        for dep in _mdvisual["deps"]:#
            if pkg_dir: _mdvisual["trace"] += [subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "--target", pkg_dir, dep])]
            else: _mdvisual["trace"] += [subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", dep])]
        
        try:
            # Check for incomplete dependencies
            for complete in _mdvisual["trace"]:
                complete.check_returncode()

            for dep in _mdvisual["assert_deps"]:
                _MDImport.module(dep)
            
            _mdvisual["ready"] = True
        except Exception as ex1:
            _mdvisual["exceptions"] += [ex1]
    
    return _mdvisual["ready"]


CLASSES = (
    MDEntity,
    MDCache,
    MDRange,
    MDSystem,
    MDSYSTEM_OT_Refresh,
    MDRANGE_OT_Instance_New,
    MDRANGE_OT_Geometric_Nodes_New,
    MDRANGE_OT_Particle_System_New,
    MDRANGE_OT_Hair_System_New,
    MDRANGE_OT_Mesh_New,
    MDRANGE_OT_Curve_New,
    MDRANGE_OT_Point_Cloud_New,
    MDRANGE_OT_Metaball_New,
    MDRANGE_OT_Refresh,
    MDRANGE_OT_Delete,
    MDRANGE_UL_List,
    MDENTITY_UL_List,
    MDVISUAL_PT_Main,
    MDRANGE_MT_Add_Bind
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.md_system = PointerProperty(name="MD Systems", type=MDSystem)
    bpy.types.Scene.md_changed = BoolProperty(name="Changed")
    bpy.types.Scene.md_instance = None
    bpy.types.Scene.md_exception = None


def unregister():
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.md_system
    del bpy.types.Scene.md_instance
    del bpy.types.Scene.md_exception
    del bpy.types.Scene.md_changed


if __name__ == "__main__":
    if not _mdvisual_setup():
        print(_mdvisual["exceptions"])
        raise Exception("Dependencies could't be loaded, try install MDAnalysis manually to Blender-Python")
    register()