bl_info = {
    "name":         "Additive animation modifiers",
    "author":       "Przemysław Bągard",
    "blender":      (2,7,9),
    "version":      (0,0,1),
    "location":     "Armature > Additive animation modifiers",
    "description":  "Adds additive animation tracks to current pose.",
    "category":     "Animation"
}

#usefull links:
# https://docs.blender.org/api/blender_python_api_2_74_0/bpy.app.handlers.html
# https://github.com/artellblender/additive_keyer
# https://docs.blender.org/api/blender_python_api_2_77_0/bpy.types.UILayout.html
# https://blenderartists.org/forum/showthread.php?209221-calculate-bone-location-rotation-from-fcurve-animation-data

# bpy.context.object.pose.bones['forearm.L']
# action = bpy.context.object.data.additive_animations[0].action


import bpy
from bpy.props import IntProperty, CollectionProperty, BoolProperty, StringProperty, PointerProperty 
from bpy.types import Panel, UIList
import mathutils
from mathutils import Vector, Quaternion, Euler, Matrix

from bpy.app.handlers import persistent

# Functions

def getCurve(action, bone, dpath, index):
    curveName = 'pose.bones["' + bone.name + '"].' + dpath
    curve = action.fcurves.find(curveName, index = index)
    #if curve:
    #    print(curveName + "[" + str(index) + "]" ".evaluate(" + str(bpy.context.scene.frame_current) + ") = " + str(curve.evaluate(bpy.context.scene.frame_current)))
    #else:
    #    print("No " + curveName + "[" + str(index) + "]" "!")
    return curve

def getActionLocation(action, bone, frame=1):
    pos = Vector()
    for i in range(0, 3):    
        fc = getCurve(action, bone, 'location', index = i)
        if fc != None:
            pos[i] = fc.evaluate(frame)
    return pos

def getActionRotation(action, bone, frame=1):
    rot = Quaternion()
    rot.identity()
    if bone.rotation_mode != 'QUATERNION':
        rot = Euler(Vector(), bone.rotation_mode)
        for i in range(0, 3):    
            fc = getCurve(action, bone, 'rotation_euler', index = i)
            if fc != None:
                rot[i] = fc.evaluate(frame)
        return rot.to_matrix()
    else:
        for i in range(0, 4):    
            fc = getCurve(action, bone, 'rotation_quaternion', index = i)
            if fc != None:
                rot[i] = fc.evaluate(frame)
        return rot.to_matrix()
    return rot.to_matrix()

def getActionScale(action, bone, frame=1):
    scale = Vector((1, 1, 1))
    for i in range(0, 3):    
        fc = getCurve(action, bone, 'scale', index = i)
        if fc != None:
            scale[i] = fc.evaluate(frame)
    return scale

def getActionMatrix(action, bone, frame=1):
    scale = getActionScale(action, bone, frame)
    size_matrix = Matrix.Identity(4)
    for i in range(3):
        size_matrix.col[i].magnitude = scale[i]
    rot_matrix = getActionRotation(action, bone, frame).to_4x4()
    #matrix = rot_matrix*size_matrix
    matrix = rot_matrix
    matrix.translation = getActionLocation(action, bone, frame)
    return matrix

def applyActions(obj, actions):
    current_frame = bpy.context.scene.frame_current
    bones = obj.pose.bones
    for bone in bones:
        matrix_total = Matrix()
        for action in actions:
            matrix = getActionMatrix(action, bone, current_frame)
            matrix_total = matrix_total*matrix
        bone.matrix = bone.matrix*matrix_total

def deapplyActions(obj, actions):
    current_frame = bpy.context.scene.frame_current
    bones = obj.pose.bones
    for bone in bones:
        matrix_total = Matrix()
        for action in actions:
            matrix = getActionMatrix(action, bone, current_frame)
            matrix_total = matrix_total*matrix
        bone.matrix = bone.matrix*matrix_total.inverted()

def insertKeyframe(types):
    scene = bpy.context.scene
    bones = bpy.context.selected_pose_bones
    #scene.tool_settings.use_keyframe_insert_auto = False
    for object in scene.objects:
        if object.type != 'ARMATURE':
            continue
        actions = []
        for additive_animations in object.data.additive_animations:
            if additive_animations.action and additive_animations.enabled:
                action = additive_animations.action
                actions.append(action)
        deapplyActions(object, actions)
    for type in types:
        bpy.ops.anim.keyframe_insert_menu(type=type)
    for object in scene.objects:
        if object.type != 'ARMATURE':
            continue
        actions = []
        for additive_animations in object.data.additive_animations:
            if additive_animations.action and additive_animations.enabled:
                action = additive_animations.action
                actions.append(action)
        applyActions(object, actions)
    

def clearPose(obj):
    for pb in obj.pose.bones:
        #Set the rotation to 0
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion.identity()
        else:
            pb.rotation_euler = Euler(Vector(), pb.rotation_mode )
        #Set the scale to 1
        pb.scale = Vector( (1, 1, 1) )
        #Set the location at rest (edit) pose bone position
        pb.location = Vector()
        
# bpy.app.handlers.frame_change_post.clear()
# bpy.app.handlers.frame_change_post.append(additiveAnimationModifiersPostHandler)

@persistent
def additiveAnimationModifiersPreHandler(scene):
    if not scene.additive_animation_enabled:
        return
    for object in scene.objects:
        if object.type != 'ARMATURE':
            continue
        clearPose(object)

@persistent
def additiveAnimationModifiersPostHandler(scene):
    if not scene.additive_animation_enabled:
        return
    for object in scene.objects:
        if object.type != 'ARMATURE':
            continue
        actions = []
        for additive_animations in object.data.additive_animations:
            if additive_animations.action and additive_animations.enabled:
                action = additive_animations.action
                actions.append(action)
        applyActions(object, actions)
    scene.additive_animation_update_is_needed = True

@persistent
def postSceneUpdate(scene):
    if scene.additive_animation_update_is_needed == True:
        #print ('postscene: ' + str(scene.additive_animation_update_is_needed))
        for object in scene.objects:
            if object.type != 'MESH':
                continue
            object.data.update()
        scene.additive_animation_update_is_needed = False
        
# ui list item actions
class Uilist_actions(bpy.types.Operator):
    bl_idname = "additive_animations.list_action"
    bl_label = "List Action"

    action = bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", ""),
        )
    )

    def invoke(self, context, event):

        scn = context.object.data
        idx = scn.additive_animations_index

        try:
            item = scn.additive_animations[idx]
        except IndexError:
            pass

        else:
            if self.action == 'DOWN' and idx < len(scn.additive_animations) - 1:
                item_next = scn.additive_animations[idx+1].name
                scn.additive_animations.move(idx, idx + 1)
                scn.additive_animations_index += 1
                #info = 'Item %d selected' % (scn.additive_animations_index + 1)
                #self.report({'INFO'}, info)

            elif self.action == 'UP' and idx >= 1:
                item_prev = scn.additive_animations[idx-1].name
                scn.additive_animations.move(idx, idx-1)
                scn.additive_animations_index -= 1
                #info = 'Item %d selected' % (scn.additive_animations_index + 1)
                #self.report({'INFO'}, info)

            elif self.action == 'REMOVE':
                #info = 'Item %s removed from list' % (scn.additive_animations[scn.additive_animations_index].name)
                scn.additive_animations_index -= 1
                #self.report({'INFO'}, info)
                scn.additive_animations.remove(idx)

        if self.action == 'ADD':
            item = scn.additive_animations.add()
            item.id = len(scn.additive_animations)
            scn.additive_animations_index = (len(scn.additive_animations)-1)
            #info = '%s added to list' % (item.name)
            #self.report({'INFO'}, info)

        return {"FINISHED"}

# -------------------------------------------------------------------
# draw
# -------------------------------------------------------------------

# additive_animations list
class AdditiveAnimation_items(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(0.95)
        split2 = split.split(0.2)
        
        split2.label("Action: %d" % (index))
        split2.prop(item, "action", text="", emboss=True, translate=False)
        split.prop(item, "enabled", text="", emboss=False, translate=False, icon='VISIBLE_IPO_ON' if item.enabled else 'VISIBLE_IPO_OFF', toggle=True, icon_only=True)

    def invoke(self, context, event):
        pass   

# draw the panel
class UIListPanelExample(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Additive animation modifiers"
    bl_idname = "OBJECT_PT_additive_animation_modifiers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    def draw(self, context):
        layout = self.layout
        object = context.object
        
        if not object or object.type != 'ARMATURE':
            return
        armature = object.data

        row = layout.row()
        row.prop(context.scene, "additive_animation_enabled", text="Enable addon for scene")
        row = layout.row()
        row.template_list("AdditiveAnimation_items", "", armature, "additive_animations", armature, "additive_animations_index", rows=2)

        col = row.column(align=True)
        col.operator("additive_animations.list_action", icon='ZOOMIN', text="").action = 'ADD'
        col.operator("additive_animations.list_action", icon='ZOOMOUT', text="").action = 'REMOVE'
        col.separator()
        col.operator("additive_animations.list_action", icon='TRIA_UP', text="").action = 'UP'
        col.operator("additive_animations.list_action", icon='TRIA_DOWN', text="").action = 'DOWN'

        row = layout.row()
        col = row.column(align=True)
        col.operator("anim.insert_keyframe_menu")

class AdditiveAnimationInsertKeyframeMenu(bpy.types.Menu):
    bl_idname = "ADDITIVE_ANIMATION_insert_keyframe_menu"
    bl_label = "Insert keyframe menu"
    # Set the menu operators and draw functions
    def draw(self, context):
        layout = self.layout
        layout.operator("additive_animations.insert_key_loc", text="Insert key loc")
        layout.operator("additive_animations.insert_key_rot", text="Insert key rot")
        #layout.operator("additive_animations.insert_key_scale", text="Insert key scale")
        layout.operator("additive_animations.insert_key_locrot", text="Insert key loc and rot")
        #layout.operator("additive_animations.insert_key_locrotscale", text="Insert key loc and rot and scale")
        #layout.operator("additive_animations.insert_key_loc", text="Insert key loc").type = 'ACTIVE'
        #layout.operator("rigidbody.objects_add", text="B Add Passive").type = 'PASSIVE'
        #layout.prop(context.scene.render, "engine")

# insert rotation keyframe
class AdditiveAnimationShowMenuOperator(bpy.types.Operator):
    bl_idname = "anim.insert_keyframe_menu"
    bl_label = "Show insert keyframe menu"
    bl_description = "Shows menu with insert key rotation without additive animation modifiers"

    def execute(self, context):
        bpy.ops.wm.call_menu(name="ADDITIVE_ANIMATION_insert_keyframe_menu")
        return{'FINISHED'}
        

class Uilist_insertKeyLoc(bpy.types.Operator):
    bl_idname = "additive_animations.insert_key_loc"
    bl_label = "Insert location without additive animation"
    bl_description = "Insert key location without additive animation modifiers"

    def execute(self, context):
        insertKeyframe(['Location']);
        return{'FINISHED'}

class Uilist_insertKeyRot(bpy.types.Operator):
    bl_idname = "additive_animations.insert_key_rot"
    bl_label = "Insert rot without additive animation"
    bl_description = "Insert key rotation without additive animation modifiers"

    def execute(self, context):
        insertKeyframe(['Rotation']);
        return{'FINISHED'}

#class Uilist_insertKeyScale(bpy.types.Operator):
#    bl_idname = "additive_animations.insert_key_scale"
#    bl_label = "Insert scale without additive animation"
#    bl_description = "Insert key scale without additive animation modifiers"
#
#    def execute(self, context):
#        insertKeyframe(['Scaling']);
#        return{'FINISHED'}

class Uilist_insertKeyLocRot(bpy.types.Operator):
    bl_idname = "additive_animations.insert_key_locrot"
    bl_label = "Insert location and rotation without additive animation"
    bl_description = "Insert key location and rotation without additive animation modifiers"

    def execute(self, context):
        insertKeyframe(['Location', 'Rotation']);
        return{'FINISHED'}

#class Uilist_insertKeyLocRotScale(bpy.types.Operator):
#    bl_idname = "additive_animations.insert_key_locrotscale"
#    bl_label = "Insert location and rotation and scale without additive animation"
#    bl_description = "Insert key location and rotation and scale without additive animation modifiers"
#
#    def execute(self, context):
#        insertKeyframe(['Location', 'Rotation', 'Scaling']);
#        return{'FINISHED'}
        
# Create additive_animations property group
class CustomProp(bpy.types.PropertyGroup):
    '''name = StringProperty() '''
    id = IntProperty()
    enabled = BoolProperty(default=True);
    action = PointerProperty(name="Action", type=bpy.types.Action)

# bpy.data.window_managers[0].keyconfigs.active.keymaps['Mesh'].keymap_items.new('op.idname',value='PRESS',type=' A',ctrl=True,alt=True,shift=True,oskey=True)
# bpy.data.window_managers[0].keyconfigs.active.keymaps['Animation'].keymap_items.new('op.idname',value='PRESS',type=' A',ctrl=True,alt=True,shift=True,oskey=True)

# -------------------------------------------------------------------
# register
# -------------------------------------------------------------------

def add_to_menu(self, context):
    self.layout.operator("additive_animations.insert_key_rot")

bpy.utils.register_class(AdditiveAnimationInsertKeyframeMenu)
    
def register():
    bpy.utils.register_module(__name__)
    bpy.types.Armature.additive_animations = CollectionProperty(type=CustomProp)
    bpy.types.Armature.additive_animations_index = IntProperty()
    bpy.types.Scene.additive_animation_enabled = BoolProperty(default=False)
    bpy.types.Scene.additive_animation_update_is_needed = BoolProperty(default=False)
    bpy.app.handlers.scene_update_pre.append(postSceneUpdate)
    bpy.app.handlers.frame_change_pre.append(additiveAnimationModifiersPreHandler)
    bpy.app.handlers.frame_change_post.append(additiveAnimationModifiersPostHandler)
    #bpy.types.ANIM_OT_keyframe_insert_menu.append(add_to_menu)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Armature.additive_animations
    del bpy.types.Armature.additive_animations_index
    del bpy.types.Scene.additive_animation_enabled
    del bpy.types.Scene.additive_animation_update_is_needed
    bpy.app.handlers.scene_update_pre.remove(postSceneUpdate)
    bpy.app.handlers.frame_change_post.remove(additiveAnimationModifiersPostHandler)
    #bpy.types.ANIM_OT_keyframe_insert_menu.remove(add_to_menu)
    
if __name__ == "__main__":
    register()
