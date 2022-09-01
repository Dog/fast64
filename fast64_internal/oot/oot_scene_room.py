import math, os, bpy, bmesh, mathutils
from bpy.utils import register_class, unregister_class
from io import BytesIO

from ..utility import *
from .oot_utility import *
from .oot_constants import *
from ..f3d.f3d_gbi import *

from .oot_actor import *

# from .oot_collision import *
from .oot_cutscene import *


class OOTSceneProperties(bpy.types.PropertyGroup):
    write_dummy_room_list: bpy.props.BoolProperty(
        name="Dummy Room List",
        default=False,
        description=(
            "When exporting the scene to C, use NULL for the pointers to room "
            "start/end offsets, instead of the appropriate symbols"
        ),
    )


class OOT_SearchMusicSeqEnumOperator(bpy.types.Operator):
    bl_idname = "object.oot_search_music_seq_enum_operator"
    bl_label = "Search Music Sequence"
    bl_property = "ootMusicSeq"
    bl_options = {"REGISTER", "UNDO"}

    ootMusicSeq: bpy.props.EnumProperty(items=ootEnumMusicSeq, default="0x02")
    headerIndex: bpy.props.IntProperty(default=0, min=0)
    objName: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects[self.objName]
        if self.headerIndex == 0:
            sceneHeader = obj.ootSceneHeader
        elif self.headerIndex == 1:
            sceneHeader = obj.ootAlternateSceneHeaders.childNightHeader
        elif self.headerIndex == 2:
            sceneHeader = obj.ootAlternateSceneHeaders.adultDayHeader
        elif self.headerIndex == 3:
            sceneHeader = obj.ootAlternateSceneHeaders.adultNightHeader
        else:
            sceneHeader = obj.ootAlternateSceneHeaders.cutsceneHeaders[self.headerIndex - 4]

        sceneHeader.musicSeq = self.ootMusicSeq
        bpy.context.region.tag_redraw()
        self.report({"INFO"}, "Selected: " + self.ootMusicSeq)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}


class OOT_SearchObjectEnumOperator(bpy.types.Operator):
    bl_idname = "object.oot_search_object_enum_operator"
    bl_label = "Search Object ID"
    bl_property = "ootObjectID"
    bl_options = {"REGISTER", "UNDO"}

    ootObjectID: bpy.props.EnumProperty(items=ootEnumObjectID, default="OBJECT_HUMAN")
    headerIndex: bpy.props.IntProperty(default=0, min=0)
    index: bpy.props.IntProperty(default=0, min=0)
    objName: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects[self.objName]
        if self.headerIndex == 0:
            roomHeader = obj.ootRoomHeader
        elif self.headerIndex == 1:
            roomHeader = obj.ootAlternateRoomHeaders.childNightHeader
        elif self.headerIndex == 2:
            roomHeader = obj.ootAlternateRoomHeaders.adultDayHeader
        elif self.headerIndex == 3:
            roomHeader = obj.ootAlternateRoomHeaders.adultNightHeader
        else:
            roomHeader = obj.ootAlternateRoomHeaders.cutsceneHeaders[self.headerIndex - 4]

        roomHeader.objectList[self.index].objectID = self.ootObjectID
        bpy.context.region.tag_redraw()
        self.report({"INFO"}, "Selected: " + self.ootObjectID)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}


class OOT_SearchSceneEnumOperator(bpy.types.Operator):
    bl_idname = "object.oot_search_scene_enum_operator"
    bl_label = "Choose Scene"
    bl_property = "ootSceneID"
    bl_options = {"REGISTER", "UNDO"}

    ootSceneID: bpy.props.EnumProperty(items=ootEnumSceneID, default="SCENE_YDAN")

    def execute(self, context):
        context.scene.ootSceneOption = self.ootSceneID
        bpy.context.region.tag_redraw()
        self.report({"INFO"}, "Selected: " + self.ootSceneID)
        return {"FINISHED"}

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}


def drawAlternateRoomHeaderProperty(layout, headerProp, objName):
    headerSetup = layout.column()
    # headerSetup.box().label(text = "Alternate Headers")
    headerSetupBox = headerSetup.column()

    headerSetupBox.row().prop(headerProp, "headerMenuTab", expand=True)
    if headerProp.headerMenuTab == "Child Night":
        drawRoomHeaderProperty(headerSetupBox, headerProp.childNightHeader, None, 1, objName)
    elif headerProp.headerMenuTab == "Adult Day":
        drawRoomHeaderProperty(headerSetupBox, headerProp.adultDayHeader, None, 2, objName)
    elif headerProp.headerMenuTab == "Adult Night":
        drawRoomHeaderProperty(headerSetupBox, headerProp.adultNightHeader, None, 3, objName)
    elif headerProp.headerMenuTab == "Cutscene":
        prop_split(headerSetup, headerProp, "currentCutsceneIndex", "Cutscene Index")
        drawAddButton(headerSetup, len(headerProp.cutsceneHeaders), "Room", None, objName)
        index = headerProp.currentCutsceneIndex
        if index - 4 < len(headerProp.cutsceneHeaders):
            drawRoomHeaderProperty(headerSetup, headerProp.cutsceneHeaders[index - 4], None, index, objName)
        else:
            headerSetup.label(text="No cutscene header for this index.", icon="QUESTION")


class OOTExitProperty(bpy.types.PropertyGroup):
    expandTab: bpy.props.BoolProperty(name="Expand Tab")

    exitIndex: bpy.props.EnumProperty(items=ootEnumExitIndex, default="Default")
    exitIndexCustom: bpy.props.StringProperty(default="0x0000")

    # These are used when adding an entry to gEntranceTable
    scene: bpy.props.EnumProperty(items=ootEnumSceneID, default="SCENE_YDAN")
    sceneCustom: bpy.props.StringProperty(default="SCENE_YDAN")

    # These are used when adding an entry to gEntranceTable
    continueBGM: bpy.props.BoolProperty(default=False)
    displayTitleCard: bpy.props.BoolProperty(default=True)
    fadeInAnim: bpy.props.EnumProperty(items=ootEnumTransitionAnims, default="0x02")
    fadeInAnimCustom: bpy.props.StringProperty(default="0x02")
    fadeOutAnim: bpy.props.EnumProperty(items=ootEnumTransitionAnims, default="0x02")
    fadeOutAnimCustom: bpy.props.StringProperty(default="0x02")


def drawExitProperty(layout, exitProp, index, headerIndex, objName):
    box = layout.box()
    box.prop(
        exitProp, "expandTab", text="Exit " + str(index + 1), icon="TRIA_DOWN" if exitProp.expandTab else "TRIA_RIGHT"
    )
    if exitProp.expandTab:
        drawCollectionOps(box, index, "Exit", headerIndex, objName)
        drawEnumWithCustom(box, exitProp, "exitIndex", "Exit Index", "")
        if exitProp.exitIndex != "Custom":
            box.label(text='This is unfinished, use "Custom".')
            exitGroup = box.column()
            exitGroup.enabled = False
            drawEnumWithCustom(exitGroup, exitProp, "scene", "Scene", "")
            exitGroup.prop(exitProp, "continueBGM", text="Continue BGM")
            exitGroup.prop(exitProp, "displayTitleCard", text="Display Title Card")
            drawEnumWithCustom(exitGroup, exitProp, "fadeInAnim", "Fade In Animation", "")
            drawEnumWithCustom(exitGroup, exitProp, "fadeOutAnim", "Fade Out Animation", "")


class OOTObjectProperty(bpy.types.PropertyGroup):
    expandTab: bpy.props.BoolProperty(name="Expand Tab")
    objectID: bpy.props.EnumProperty(items=ootEnumObjectID, default="OBJECT_HUMAN")
    objectIDCustom: bpy.props.StringProperty(default="OBJECT_HUMAN")


def drawObjectProperty(layout, objectProp, headerIndex, index, objName):
    objItemBox = layout.column()
    objectName = getEnumName(ootEnumObjectID, objectProp.objectID)
    # objItemBox.prop(
    #    objectProp, "expandTab", text=objectName, icon="TRIA_DOWN" if objectProp.expandTab else "TRIA_RIGHT"
    # )
    # if objectProp.expandTab:
    row = objItemBox.row()
    row.label(text=f"{objectName}")
    buttons = row.row(align=True)
    objSearch = buttons.operator(OOT_SearchObjectEnumOperator.bl_idname, icon="VIEWZOOM", text="Select")
    drawCollectionOps(buttons, index, "Object", headerIndex, objName, compact=True)
    objSearch.objName = objName
    objSearch.headerIndex = headerIndex if headerIndex is not None else 0
    objSearch.index = index
    # objItemBox.column().label(text="ID: " + objectName)
    # prop_split(objItemBox, objectProp, "objectID", name = "ID")
    if objectProp.objectID == "Custom":
        prop_split(objItemBox, objectProp, "objectIDCustom", "Object ID Custom")


class OOTLightProperty(bpy.types.PropertyGroup):
    ambient: bpy.props.FloatVectorProperty(
        name="Ambient Color", size=4, min=0, max=1, default=(70 / 255, 40 / 255, 57 / 255, 1), subtype="COLOR"
    )
    useCustomDiffuse0: bpy.props.BoolProperty(name="Custom Light")
    useCustomDiffuse1: bpy.props.BoolProperty(name="Custom Light")
    diffuse0: bpy.props.FloatVectorProperty(
        name="", size=4, min=0, max=1, default=(180 / 255, 154 / 255, 138 / 255, 1), subtype="COLOR"
    )
    diffuse1: bpy.props.FloatVectorProperty(
        name="", size=4, min=0, max=1, default=(20 / 255, 20 / 255, 60 / 255, 1), subtype="COLOR"
    )
    diffuse0Custom: bpy.props.PointerProperty(name="Diffuse 0", type=bpy.types.Light)
    diffuse1Custom: bpy.props.PointerProperty(name="Diffuse 1", type=bpy.types.Light)
    zeroDiffuse0: bpy.props.BoolProperty(name="Zero Direction", default=False)
    zeroDiffuse1: bpy.props.BoolProperty(name="Zero Direction", default=False)
    fogColor: bpy.props.FloatVectorProperty(
        name="", size=4, min=0, max=1, default=(140 / 255, 120 / 255, 110 / 255, 1), subtype="COLOR"
    )
    fogNear: bpy.props.IntProperty(name="", default=993, min=0, max=2**10 - 1)
    transitionSpeed: bpy.props.IntProperty(name="", default=1, min=0, max=63)
    fogFar: bpy.props.IntProperty(name="", default=0x3200, min=0, max=2**16 - 1)
    expandTab: bpy.props.BoolProperty(name="Expand Tab")


class OOTLightGroupProperty(bpy.types.PropertyGroup):
    expandTab: bpy.props.BoolProperty()
    menuTab: bpy.props.EnumProperty(items=ootEnumLightGroupMenu)
    dawn: bpy.props.PointerProperty(type=OOTLightProperty)
    day: bpy.props.PointerProperty(type=OOTLightProperty)
    dusk: bpy.props.PointerProperty(type=OOTLightProperty)
    night: bpy.props.PointerProperty(type=OOTLightProperty)
    defaultsSet: bpy.props.BoolProperty()


def drawLightGroupProperty(layout, lightGroupProp):

    box = layout.column()
    box.row().prop(lightGroupProp, "menuTab", expand=True)
    if lightGroupProp.menuTab == "Dawn":
        drawLightProperty(box, lightGroupProp.dawn, "Dawn", False, None, None, None)
    if lightGroupProp.menuTab == "Day":
        drawLightProperty(box, lightGroupProp.day, "Day", False, None, None, None)
    if lightGroupProp.menuTab == "Dusk":
        drawLightProperty(box, lightGroupProp.dusk, "Dusk", False, None, None, None)
    if lightGroupProp.menuTab == "Night":
        drawLightProperty(box, lightGroupProp.night, "Night", False, None, None, None)


def drawLightProperty(layout, lightProp, name, showExpandTab, index, sceneHeaderIndex, objName):
    if showExpandTab:
        box = layout.box().column()
        box.prop(lightProp, "expandTab", text=name, icon="TRIA_DOWN" if lightProp.expandTab else "TRIA_RIGHT")
        expandTab = lightProp.expandTab
    else:
        box = layout
        expandTab = True

    if expandTab:
        if index is not None:
            drawCollectionOps(box, index, "Light", sceneHeaderIndex, objName)
        prop_split(box, lightProp, "ambient", "Ambient Color")

        if lightProp.useCustomDiffuse0:
            prop_split(box, lightProp, "diffuse0Custom", "Diffuse 0")
            box.label(text="Make sure light is not part of scene hierarchy.", icon="FILE_PARENT")
            box.prop(lightProp, "useCustomDiffuse0")
        else:
            prop_split(box, lightProp, "diffuse0", "Diffuse 0")
            row = box.row()
            row.prop(lightProp, "useCustomDiffuse0")
            row.prop(lightProp, "zeroDiffuse0")

        if lightProp.useCustomDiffuse1:
            prop_split(box, lightProp, "diffuse1Custom", "Diffuse 1")
            box.label(text="Make sure light is not part of scene hierarchy.", icon="FILE_PARENT")
            box.prop(lightProp, "useCustomDiffuse1")
        else:
            prop_split(box, lightProp, "diffuse1", "Diffuse 1")
            row = box.row()
            row.prop(lightProp, "useCustomDiffuse1")
            row.prop(lightProp, "zeroDiffuse1")

        prop_split(box, lightProp, "fogColor", "Fog Color")
        prop_split(box, lightProp, "fogNear", "Fog Near")
        prop_split(box, lightProp, "fogFar", "Fog Far")
        prop_split(box, lightProp, "transitionSpeed", "Transition Speed")


class OOTSceneTableEntryProperty(bpy.types.PropertyGroup):
    drawConfig: bpy.props.EnumProperty(items=ootEnumDrawConfig, name="Scene Draw Config")
    drawConfigCustom: bpy.props.StringProperty(name="Scene Draw Config Custom")
    hasTitle: bpy.props.BoolProperty(default=True)


class OOTExtraCutsceneProperty(bpy.types.PropertyGroup):
    csObject: bpy.props.PointerProperty(name="Cutscene Object", type=bpy.types.Object)


def onMenuTabChange(self, context: bpy.types.Context):
    def callback(thisHeader, otherObj: bpy.types.Object):
        if otherObj.ootEmptyType == "Scene":
            header = otherObj.ootSceneHeader
        else:
            header = otherObj.ootRoomHeader

        if thisHeader.menuTab != "Alternate" and header.menuTab == "Alternate":
            header.menuTab = "General"
        if thisHeader.menuTab == "Alternate" and header.menuTab != "Alternate":
            header.menuTab = "Alternate"

    onHeaderPropertyChange(self, context, callback)


def onHeaderMenuTabChange(self, context: bpy.types.Context):
    def callback(thisHeader, otherObj: bpy.types.Object):
        if otherObj.ootEmptyType == "Scene":
            header = otherObj.ootAlternateSceneHeaders
        else:
            header = otherObj.ootAlternateRoomHeaders

        header.headerMenuTab = thisHeader.headerMenuTab
        header.currentCutsceneIndex = thisHeader.currentCutsceneIndex

    onHeaderPropertyChange(self, context, callback)


def onHeaderPropertyChange(self, context: bpy.types.Context, callback: Callable[[any, bpy.types.Object], None]):
    if not bpy.context.scene.ootHeaderTabAffectsVisibility or bpy.context.scene.ootActiveHeaderLock:
        return
    bpy.context.scene.ootActiveHeaderLock = True

    thisHeader = self
    thisObj = context.object
    otherObjs = [
        obj
        for obj in bpy.data.objects
        if (obj.ootEmptyType == "Scene" or obj.ootEmptyType == "Room") and obj != thisObj
    ]

    for otherObj in otherObjs:
        callback(thisHeader, otherObj)

    setAllActorsVisibility(self, context)

    bpy.context.scene.ootActiveHeaderLock = False


class OOTSceneHeaderProperty(bpy.types.PropertyGroup):
    expandTab: bpy.props.BoolProperty(name="Expand Tab")
    usePreviousHeader: bpy.props.BoolProperty(name="Use Previous Header", default=True)

    globalObject: bpy.props.EnumProperty(
        name="Global Object", default="OBJECT_GAMEPLAY_DANGEON_KEEP", items=ootEnumGlobalObject
    )
    globalObjectCustom: bpy.props.StringProperty(name="Global Object Custom", default="0x00")
    naviCup: bpy.props.EnumProperty(name="Navi Hints", default="0x00", items=ootEnumNaviHints)
    naviCupCustom: bpy.props.StringProperty(name="Navi Hints Custom", default="0x00")

    skyboxID: bpy.props.EnumProperty(name="Skybox", items=ootEnumSkybox, default="0x01")
    skyboxIDCustom: bpy.props.StringProperty(name="Skybox ID", default="0")
    skyboxCloudiness: bpy.props.EnumProperty(name="Cloudiness", items=ootEnumCloudiness, default="0x00")
    skyboxCloudinessCustom: bpy.props.StringProperty(name="Cloudiness ID", default="0x00")
    skyboxLighting: bpy.props.EnumProperty(name="Skybox Lighting", items=ootEnumSkyboxLighting, default="false")
    skyboxLightingCustom: bpy.props.StringProperty(name="Skybox Lighting Custom", default="0x00")

    mapLocation: bpy.props.EnumProperty(name="Map Location", items=ootEnumMapLocation, default="0x00")
    mapLocationCustom: bpy.props.StringProperty(name="Skybox Lighting Custom", default="0x00")
    cameraMode: bpy.props.EnumProperty(name="Camera Mode", items=ootEnumCameraMode, default="0x00")
    cameraModeCustom: bpy.props.StringProperty(name="Camera Mode Custom", default="0x00")

    musicSeq: bpy.props.EnumProperty(name="Music Sequence", items=ootEnumMusicSeq, default="0x02")
    musicSeqCustom: bpy.props.StringProperty(name="Music Sequence ID", default="0x00")
    nightSeq: bpy.props.EnumProperty(name="Nighttime SFX", items=ootEnumNightSeq, default="0x00")
    nightSeqCustom: bpy.props.StringProperty(name="Nighttime SFX ID", default="0x00")
    audioSessionPreset: bpy.props.EnumProperty(
        name="Audio Session Preset", items=ootEnumAudioSessionPreset, default="0x00"
    )
    audioSessionPresetCustom: bpy.props.StringProperty(name="Audio Session Preset", default="0x00")

    timeOfDayLights: bpy.props.PointerProperty(type=OOTLightGroupProperty, name="Time Of Day Lighting")
    lightList: bpy.props.CollectionProperty(type=OOTLightProperty, name="Lighting List")
    exitList: bpy.props.CollectionProperty(type=OOTExitProperty, name="Exit List")

    writeCutscene: bpy.props.BoolProperty(name="Write Cutscene")
    csWriteType: bpy.props.EnumProperty(name="Cutscene Data Type", items=ootEnumCSWriteType, default="Embedded")
    csWriteCustom: bpy.props.StringProperty(name="CS hdr var:", default="")
    csWriteObject: bpy.props.PointerProperty(name="Cutscene Object", type=bpy.types.Object)

    # These properties are for the deprecated "Embedded" cutscene type. They have
    # not been removed as doing so would break any existing scenes made with this
    # type of cutscene data.
    csEndFrame: bpy.props.IntProperty(name="End Frame", min=0, default=100)
    csWriteTerminator: bpy.props.BoolProperty(name="Write Terminator (Code Execution)")
    csTermIdx: bpy.props.IntProperty(name="Index", min=0)
    csTermStart: bpy.props.IntProperty(name="Start Frm", min=0, default=99)
    csTermEnd: bpy.props.IntProperty(name="End Frm", min=0, default=100)
    csLists: bpy.props.CollectionProperty(type=OOTCSListProperty, name="Cutscene Lists")

    extraCutscenes: bpy.props.CollectionProperty(type=OOTExtraCutsceneProperty, name="Extra Cutscenes")

    sceneTableEntry: bpy.props.PointerProperty(type=OOTSceneTableEntryProperty)

    menuTab: bpy.props.EnumProperty(name="Menu", items=ootEnumSceneMenu, update=onMenuTabChange)
    altMenuTab: bpy.props.EnumProperty(name="Menu", items=ootEnumSceneMenuAlternate)

    appendNullEntrance: bpy.props.BoolProperty(
        name="Append Null Entrance",
        description="Add an additional {0, 0} to the end of the EntranceEntry list.",
        default=False,
    )


def drawSceneTableEntryProperty(layout, sceneTableEntryProp):
    drawEnumWithCustom(layout, sceneTableEntryProp, "drawConfig", "Draw Config", "")


def drawSceneHeaderProperty(layout, sceneProp, dropdownLabel, headerIndex, objName):
    if dropdownLabel is not None:
        layout.prop(
            sceneProp, "expandTab", text=dropdownLabel, icon="TRIA_DOWN" if sceneProp.expandTab else "TRIA_RIGHT"
        )
        if not sceneProp.expandTab:
            return
    if headerIndex is not None and headerIndex > 3:
        drawCollectionOps(layout, headerIndex - 4, "Scene", None, objName)

    if headerIndex is not None and headerIndex > 0 and headerIndex < 4:
        layout.prop(sceneProp, "usePreviousHeader", text="Use Previous Header")
        if sceneProp.usePreviousHeader:
            return

    if headerIndex is None or headerIndex == 0:
        layout.row().prop(sceneProp, "menuTab", expand=True)
        menuTab = sceneProp.menuTab
    else:
        layout.row().prop(sceneProp, "altMenuTab", expand=True)
        menuTab = sceneProp.altMenuTab

    if menuTab == "General":
        general = layout.column()
        general.box().label(text="General")
        drawEnumWithCustom(general, sceneProp, "globalObject", "Global Object", "")
        drawEnumWithCustom(general, sceneProp, "naviCup", "Navi Hints", "")
        if headerIndex is None or headerIndex == 0:
            drawSceneTableEntryProperty(general, sceneProp.sceneTableEntry)
        general.prop(sceneProp, "appendNullEntrance")

        skyboxAndSound = layout.column()
        skyboxAndSound.box().label(text="Skybox And Sound")
        drawEnumWithCustom(skyboxAndSound, sceneProp, "skyboxID", "Skybox", "")
        drawEnumWithCustom(skyboxAndSound, sceneProp, "skyboxCloudiness", "Cloudiness", "")
        drawEnumWithCustom(skyboxAndSound, sceneProp, "musicSeq", "Music Sequence", "")
        musicSearch = skyboxAndSound.operator(OOT_SearchMusicSeqEnumOperator.bl_idname, icon="VIEWZOOM")
        musicSearch.objName = objName
        musicSearch.headerIndex = headerIndex if headerIndex is not None else 0
        drawEnumWithCustom(skyboxAndSound, sceneProp, "nightSeq", "Nighttime SFX", "")
        drawEnumWithCustom(skyboxAndSound, sceneProp, "audioSessionPreset", "Audio Session Preset", "")

        cameraAndWorldMap = layout.column()
        cameraAndWorldMap.box().label(text="Camera And World Map")
        drawEnumWithCustom(cameraAndWorldMap, sceneProp, "mapLocation", "Map Location", "")
        drawEnumWithCustom(cameraAndWorldMap, sceneProp, "cameraMode", "Camera Mode", "")

    elif menuTab == "Lighting":
        lighting = layout.column()
        lighting.box().label(text="Lighting List")
        drawEnumWithCustom(lighting, sceneProp, "skyboxLighting", "Lighting Mode", "")
        if sceneProp.skyboxLighting == "false":  # Time of Day
            drawLightGroupProperty(lighting, sceneProp.timeOfDayLights)
        else:
            for i in range(len(sceneProp.lightList)):
                drawLightProperty(lighting, sceneProp.lightList[i], "Lighting " + str(i), True, i, headerIndex, objName)
            drawAddButton(lighting, len(sceneProp.lightList), "Light", headerIndex, objName)

    elif menuTab == "Cutscene":
        cutscene = layout.column()
        r = cutscene.row()
        r.prop(sceneProp, "writeCutscene", text="Write Cutscene")
        if sceneProp.writeCutscene:
            r.prop(sceneProp, "csWriteType", text="Data")
            if sceneProp.csWriteType == "Custom":
                cutscene.prop(sceneProp, "csWriteCustom")
            elif sceneProp.csWriteType == "Object":
                cutscene.prop(sceneProp, "csWriteObject")
            else:
                # This is the GUI setup / drawing for the properties for the
                # deprecated "Embedded" cutscene type. They have not been removed
                # as doing so would break any existing scenes made with this type
                # of cutscene data.
                cutscene.label(text='Embedded cutscenes are deprecated. Please use "Object" instead.')
                cutscene.prop(sceneProp, "csEndFrame", text="End Frame")
                cutscene.prop(sceneProp, "csWriteTerminator", text="Write Terminator (Code Execution)")
                if sceneProp.csWriteTerminator:
                    r = cutscene.row()
                    r.prop(sceneProp, "csTermIdx", text="Index")
                    r.prop(sceneProp, "csTermStart", text="Start Frm")
                    r.prop(sceneProp, "csTermEnd", text="End Frm")
                collectionType = "CSHdr." + str(0 if headerIndex is None else headerIndex)
                for i, p in enumerate(sceneProp.csLists):
                    drawCSListProperty(cutscene, p, i, objName, collectionType)
                drawCSAddButtons(cutscene, objName, collectionType)
        if headerIndex is None or headerIndex == 0:
            cutscene.label(text="Extra cutscenes (not in any header):")
            for i in range(len(sceneProp.extraCutscenes)):
                box = cutscene.box().column()
                drawCollectionOps(box, i, "extraCutscenes", None, objName, True)
                box.prop(sceneProp.extraCutscenes[i], "csObject", text="CS obj")
            if len(sceneProp.extraCutscenes) == 0:
                drawAddButton(cutscene, 0, "extraCutscenes", 0, objName)

    elif menuTab == "Exits":
        exitBox = layout.column()
        exitBox.box().label(text="Exit List")
        for i in range(len(sceneProp.exitList)):
            drawExitProperty(exitBox, sceneProp.exitList[i], i, headerIndex, objName)

        drawAddButton(exitBox, len(sceneProp.exitList), "Exit", headerIndex, objName)


class OOTBGProperty(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(type=bpy.types.Image)
    camera: bpy.props.IntProperty(name="Camera Index", min=0)
    otherModeFlags: bpy.props.StringProperty(
        name="DPSetOtherMode Flags", default="0", description="See src/code/z_room.c:func_8009638C()"
    )

    def draw(self, layout: bpy.types.UILayout, index: int, objName: str, isMulti: bool):
        box = layout.box().column()

        box.template_ID(self, "image", new="image.new", open="image.open")
        if isMulti:
            prop_split(box, self, "camera", "Camera")
        prop_split(box, self, "otherModeFlags", "Other Mode Flags")
        drawCollectionOps(box, index, "BgImage", None, objName)


class OOTRoomHeaderProperty(bpy.types.PropertyGroup):
    expandTab: bpy.props.BoolProperty(name="Expand Tab")
    menuTab: bpy.props.EnumProperty(items=ootEnumRoomMenu, update=onMenuTabChange)
    altMenuTab: bpy.props.EnumProperty(items=ootEnumRoomMenuAlternate)
    usePreviousHeader: bpy.props.BoolProperty(name="Use Previous Header", default=True)

    roomIndex: bpy.props.IntProperty(name="Room Index", default=0, min=0)
    roomBehaviour: bpy.props.EnumProperty(items=ootEnumRoomBehaviour, default="0x00")
    roomBehaviourCustom: bpy.props.StringProperty(default="0x00")
    disableWarpSongs: bpy.props.BoolProperty(name="Disable Warp Songs")
    showInvisibleActors: bpy.props.BoolProperty(name="Show Invisible Actors")
    linkIdleMode: bpy.props.EnumProperty(name="Link Idle Mode", items=ootEnumLinkIdle, default="0x00")
    linkIdleModeCustom: bpy.props.StringProperty(name="Link Idle Mode Custom", default="0x00")

    useCustomBehaviourX: bpy.props.BoolProperty(name="Use Custom Behaviour X")
    useCustomBehaviourY: bpy.props.BoolProperty(name="Use Custom Behaviour Y")

    customBehaviourX: bpy.props.StringProperty(name="Custom Behaviour X", default="0x00")

    customBehaviourY: bpy.props.StringProperty(name="Custom Behaviour Y", default="0x00")

    setWind: bpy.props.BoolProperty(name="Set Wind")
    windVector: bpy.props.IntVectorProperty(name="Wind Vector", size=3, min=-127, max=127)
    windStrength: bpy.props.IntProperty(name="Wind Strength", min=0, max=255)

    leaveTimeUnchanged: bpy.props.BoolProperty(name="Leave Time Unchanged", default=True)
    timeHours: bpy.props.IntProperty(name="Hours", default=0, min=0, max=23)  # 0xFFFE
    timeMinutes: bpy.props.IntProperty(name="Minutes", default=0, min=0, max=59)
    timeSpeed: bpy.props.FloatProperty(name="Time Speed", default=1, min=-13, max=13)  # 0xA

    disableSkybox: bpy.props.BoolProperty(name="Disable Skybox")
    disableSunMoon: bpy.props.BoolProperty(name="Disable Sun/Moon")

    echo: bpy.props.StringProperty(name="Echo", default="0x00")

    objectList: bpy.props.CollectionProperty(type=OOTObjectProperty)

    meshType: bpy.props.EnumProperty(items=ootEnumMeshType, default="0")
    defaultCullDistance: bpy.props.IntProperty(name="Default Cull Distance", min=1, default=100)
    bgImageList: bpy.props.CollectionProperty(type=OOTBGProperty)
    bgImageTab: bpy.props.BoolProperty(name="BG Images")


def drawBGImageList(layout: bpy.types.UILayout, roomHeader: OOTRoomHeaderProperty, objName: str):
    box = layout.column()
    box.prop(roomHeader, "bgImageTab", text="BG Images", icon="TRIA_DOWN" if roomHeader.bgImageTab else "TRIA_RIGHT")
    if roomHeader.bgImageTab:
        imageCount = len(roomHeader.bgImageList)
        for i in range(imageCount):
            roomHeader.bgImageList[i].draw(box, i, objName, imageCount > 1)

        drawAddButton(box, len(roomHeader.bgImageList), "BgImage", None, objName)


def drawRoomHeaderProperty(layout, roomProp, dropdownLabel, headerIndex, objName):

    if dropdownLabel is not None:
        layout.prop(roomProp, "expandTab", text=dropdownLabel, icon="TRIA_DOWN" if roomProp.expandTab else "TRIA_RIGHT")
        if not roomProp.expandTab:
            return
    if headerIndex is not None and headerIndex > 3:
        drawCollectionOps(layout, headerIndex - 4, "Room", None, objName)

    if headerIndex is not None and headerIndex > 0 and headerIndex < 4:
        layout.prop(roomProp, "usePreviousHeader", text="Use Previous Header")
        if roomProp.usePreviousHeader:
            return

    if headerIndex is None or headerIndex == 0:
        layout.row().prop(roomProp, "menuTab", expand=True)
        menuTab = roomProp.menuTab
    else:
        layout.row().prop(roomProp, "altMenuTab", expand=True)
        menuTab = roomProp.altMenuTab

    if menuTab == "General":
        if headerIndex is None or headerIndex == 0:
            general = layout.column()
            general.box().label(text="General")
            prop_split(general, roomProp, "roomIndex", "Room Index")
            prop_split(general, roomProp, "meshType", "Mesh Type")
            if roomProp.meshType == "1":
                general.box().label(text="Mesh Type 1 not supported at this time.")
                drawBGImageList(general, roomProp, objName)
            if roomProp.meshType == "2":
                prop_split(general, roomProp, "defaultCullDistance", "Default Cull (Blender Units)")

        # Behaviour
        behaviourBox = layout.column()
        behaviourBox.box().label(text="Behaviour")
        drawEnumWithCustom(behaviourBox, roomProp, "roomBehaviour", "Room Behaviour", "")
        drawEnumWithCustom(behaviourBox, roomProp, "linkIdleMode", "Link Idle Mode", "")
        behaviourBox.prop(roomProp, "disableWarpSongs", text="Disable Warp Songs")
        behaviourBox.prop(roomProp, "showInvisibleActors", text="Show Invisible Actors")

        # Time
        skyboxAndTime = layout.column()
        skyboxAndTime.box().label(text="Skybox And Time")

        # Skybox
        skyboxAndTime.prop(roomProp, "disableSkybox", text="Disable Skybox")
        skyboxAndTime.prop(roomProp, "disableSunMoon", text="Disable Sun/Moon")
        skyboxAndTime.prop(roomProp, "leaveTimeUnchanged", text="Leave Time Unchanged")
        if not roomProp.leaveTimeUnchanged:
            skyboxAndTime.label(text="Time")
            timeRow = skyboxAndTime.row()
            timeRow.prop(roomProp, "timeHours", text="Hours")
            timeRow.prop(roomProp, "timeMinutes", text="Minutes")
            # prop_split(skyboxAndTime, roomProp, "timeValue", "Time Of Day")
        prop_split(skyboxAndTime, roomProp, "timeSpeed", "Time Speed")

        # Echo
        prop_split(skyboxAndTime, roomProp, "echo", "Echo")

        # Wind
        windBox = layout.column()
        windBox.box().label(text="Wind")
        windBox.prop(roomProp, "setWind", text="Set Wind")
        if roomProp.setWind:
            windBoxRow = windBox.row()
            windBoxRow.prop(roomProp, "windVector", text="")
            windBox.prop(roomProp, "windStrength", text="Strength")
            # prop_split(windBox, roomProp, "windVector", "Wind Vector")

    elif menuTab == "Objects":
        objBox = layout.column()
        objBox.box().label(text="Objects")
        for i in range(len(roomProp.objectList)):
            drawObjectProperty(objBox, roomProp.objectList[i], headerIndex, i, objName)
        drawAddButton(objBox, len(roomProp.objectList), "Object", headerIndex, objName)


class OOTAlternateSceneHeaderProperty(bpy.types.PropertyGroup):
    childNightHeader: bpy.props.PointerProperty(name="Child Night Header", type=OOTSceneHeaderProperty)
    adultDayHeader: bpy.props.PointerProperty(name="Adult Day Header", type=OOTSceneHeaderProperty)
    adultNightHeader: bpy.props.PointerProperty(name="Adult Night Header", type=OOTSceneHeaderProperty)
    cutsceneHeaders: bpy.props.CollectionProperty(type=OOTSceneHeaderProperty)

    headerMenuTab: bpy.props.EnumProperty(name="Header Menu", items=ootEnumHeaderMenu, update=onHeaderMenuTabChange)
    currentCutsceneIndex: bpy.props.IntProperty(min=4, default=4, update=onHeaderMenuTabChange)


def drawAlternateSceneHeaderProperty(layout, headerProp, objName):
    headerSetup = layout.column()
    # headerSetup.box().label(text = "Alternate Headers")
    headerSetupBox = headerSetup.column()

    headerSetupBox.row().prop(headerProp, "headerMenuTab", expand=True)
    if headerProp.headerMenuTab == "Child Night":
        drawSceneHeaderProperty(headerSetupBox, headerProp.childNightHeader, None, 1, objName)
    elif headerProp.headerMenuTab == "Adult Day":
        drawSceneHeaderProperty(headerSetupBox, headerProp.adultDayHeader, None, 2, objName)
    elif headerProp.headerMenuTab == "Adult Night":
        drawSceneHeaderProperty(headerSetupBox, headerProp.adultNightHeader, None, 3, objName)
    elif headerProp.headerMenuTab == "Cutscene":
        prop_split(headerSetup, headerProp, "currentCutsceneIndex", "Cutscene Index")
        drawAddButton(headerSetup, len(headerProp.cutsceneHeaders), "Scene", None, objName)
        index = headerProp.currentCutsceneIndex
        if index - 4 < len(headerProp.cutsceneHeaders):
            drawSceneHeaderProperty(headerSetup, headerProp.cutsceneHeaders[index - 4], None, index, objName)
        else:
            headerSetup.label(text="No cutscene header for this index.", icon="QUESTION")


class OOTAlternateRoomHeaderProperty(bpy.types.PropertyGroup):
    childNightHeader: bpy.props.PointerProperty(name="Child Night Header", type=OOTRoomHeaderProperty)
    adultDayHeader: bpy.props.PointerProperty(name="Adult Day Header", type=OOTRoomHeaderProperty)
    adultNightHeader: bpy.props.PointerProperty(name="Adult Night Header", type=OOTRoomHeaderProperty)
    cutsceneHeaders: bpy.props.CollectionProperty(type=OOTRoomHeaderProperty)

    headerMenuTab: bpy.props.EnumProperty(name="Header Menu", items=ootEnumHeaderMenu, update=onHeaderMenuTabChange)
    currentCutsceneIndex: bpy.props.IntProperty(min=4, default=4, update=onHeaderMenuTabChange)


def drawParentSceneRoom(box, obj):
    sceneObj = getSceneObj(obj)
    roomObj = getRoomObj(obj)

    # box = layout.box().column()
    box.box().column().label(text="Parent Scene/Room Settings")
    box.row().prop(obj, "ootObjectMenu", expand=True)

    if obj.ootObjectMenu == "Scene":
        if sceneObj is not None:
            drawSceneHeaderProperty(box, sceneObj.ootSceneHeader, None, None, sceneObj.name)
            if sceneObj.ootSceneHeader.menuTab == "Alternate":
                drawAlternateSceneHeaderProperty(box, sceneObj.ootAlternateSceneHeaders, sceneObj.name)
        else:
            box.label(text="This object is not part of any Scene hierarchy.", icon="OUTLINER")

    elif obj.ootObjectMenu == "Room":
        if roomObj is not None:
            drawRoomHeaderProperty(box, roomObj.ootRoomHeader, None, None, roomObj.name)
            if roomObj.ootRoomHeader.menuTab == "Alternate":
                drawAlternateRoomHeaderProperty(box, roomObj.ootAlternateRoomHeaders, roomObj.name)
        else:
            box.label(text="This object is not part of any Room hierarchy.", icon="OUTLINER")
