import maya.cmds as cmds
import os
import sys
import maya.utils
import maya.OpenMaya as OpenMaya

# Global variables
anim_path = None
export_path = None
normal_joints = []
ads_joints = []
default_namespace = ""  # slouth rig is iw4
selected_anim_files = []


# Plugin loading functions
def add_cast_plugin_to_path():
    maya_plugin_paths = os.getenv('MAYA_PLUG_IN_PATH')

    if not maya_plugin_paths:
        print("Maya plugin path environment variable not set.")
        return False

    paths = maya_plugin_paths.split(';')

    for path in paths:
        plugin_path = os.path.join(path, 'castplugin.py')
        if os.path.isfile(plugin_path):
            sys.path.append(path)
            print("castplugin.py found. Added to sys.path: %s" % path)
            return True

    print("castplugin.py not found in the Maya plugin paths.")
    return False

def add_maya_scripts_to_sys_path():
    maya_script_paths = os.getenv('MAYA_SCRIPT_PATH')

    if maya_script_paths:
        paths = maya_script_paths.split(os.pathsep)
        for path in paths:
            if path not in sys.path:
                print("Adding %s to sys.path" % path)
                sys.path.append(path)
        return True
    else:
        print("MAYA_SCRIPT_PATH environment variable not found.")
        return False

# Initialize plugins
plugin_found = add_cast_plugin_to_path()
if plugin_found:
    try:
        import castplugin
    except:
        print("Failed to import castplugin")

if add_maya_scripts_to_sys_path():
    try:
        import CoDMayaTools
        from CoDMayaTools import OBJECT_NAMES, CreateXModelWindow, GeneralWindow_ExportSelected
        print("Successfully imported CoDMayaTools")
    except ImportError as e:
        print("Error importing CoDMayaTools: %s" % str(e))
else:
    print("Could not add Maya scripts to sys.path")



def select_anim_files_dialog(*args):
    global anim_path, selected_anim_files
    selected = cmds.fileDialog2(fileMode=4, dialogStyle=2, caption="Select cast files to rxport", fileFilter="*.cast")

    if selected:
        selected_anim_files = selected
        anim_path = os.path.dirname(selected[0])
        print("[ManyAnims] Animation path set to: %s" % anim_path)
        print("[ManyAnims] Selected %d file(s)" % len(selected_anim_files))
        cmds.confirmDialog(title="Animations Selected", message="Selected %d animation(s)." % len(selected_anim_files), button=["OK"])
        enable_ui_elements_if_paths_selected()
    else:
        selected_anim_files = []
        cmds.confirmDialog(title="No Selection", message="No animations selected.", button=["OK"])


def on_export(*args):
        if anim_path and export_path:
            load_cast_from_path(anim_path)
        else:
            cmds.confirmDialog(title="Error", message="Please select animations and export path first.", button=["OK"])


def force_update_codmaya_menu_checkbox(item_name, desired_state):
    if cmds.menuItem(item_name, exists=True):
        cmds.menuItem(item_name, edit=True, checkBox=desired_state)

def create_progress_bar(numfiles):
    if cmds.control("ManyAsserts_progress", exists=True):
        cmds.deleteUI("ManyAsserts_progress")
    window = cmds.window("ManyAsserts_progress", title="Exporting Animations")
    cmds.columnLayout()
    progress = cmds.progressBar("ManyAsserts_progress", width=300, maxValue=numfiles)
    cmds.showWindow(window)
    return progress

def update_progress_bar(progress_control, current_value):
    cmds.progressBar(progress_control, edit=True, progress=current_value)
    cmds.refresh()

def close_progress_bar():
    if cmds.control("ManyAsserts_progress", exists=True):
        cmds.deleteUI("ManyAsserts_progress")

def set_anim_path(*args):
    global anim_path
    selected = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption="Select Animation Folder")
    if selected:
        anim_path = selected[0]
        cmds.confirmDialog(title="Anim Path Selected", message="Anim Path: " + anim_path, button=["OK"])
        enable_ui_elements_if_paths_selected()

def set_export_path(*args):
    global export_path
    selected = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption="Select Export Folder")
    if selected:
        export_path = selected[0]
        cmds.confirmDialog(title="Export Path Selected", message="Export Path: " + export_path, button=["OK"])
        enable_ui_elements_if_paths_selected()

def enable_ui_elements_if_paths_selected():
    global anim_path, export_path
    if anim_path and export_path:
        toggle_ui_elements(True)

def toggle_ui_elements(enable):
    cmds.menuItem(export_button, edit=True, enable=enable)

def load_cast_from_path(anim_path):
    files_to_process = selected_anim_files or [os.path.join(anim_path, f) for f in os.listdir(anim_path) if f.endswith(".cast")]
    if not files_to_process:
        cmds.confirmDialog(title="No animations", message="No .cast files to process.", button=["OK"])
        return

    progress_control = create_progress_bar(len(files_to_process))

    for idx, anim_file_path in enumerate(files_to_process, 1):
        anim_file = os.path.basename(anim_file_path)
        print("Loading animation file: %s" % anim_file_path)
        castplugin.importCast(anim_file_path)
        export_xanim_file(anim_file_path, export_path)
        update_progress_bar(progress_control, idx)

    close_progress_bar()
    print("Processed %d animation(s)." % len(files_to_process))

    # Reset the scene after all animations are processed
    castplugin.utilityClearAnimation()

original_save_reminder = CoDMayaTools.SaveReminder

def modified_save_reminder(allow_unsaved=True):
    return True

def export_xanim_file(input_file_path, output_directory):
    ext = ".xanim_export"
    output_file_path = os.path.join(output_directory, os.path.basename(input_file_path).replace('.cast', ext))
    print("Exporting to path: %s" % output_file_path)

    filename_lower = os.path.basename(input_file_path).lower()
    is_ads = "up" in filename_lower or "down" in filename_lower
    is_add = "jump" in filename_lower or "jump_land" in filename_lower or "walk_f" in filename_lower or "fall" in filename_lower
    is_dwl = "lh_fire" in filename_lower or "lh_idle" in filename_lower or "lh_reload" in filename_lower or "lh_reload_empty" in filename_lower or "lh_swim_uw_idle" in filename_lower
    is_dwr = "rh_fire" in filename_lower or "rh_idle" in filename_lower or "rh_reload" in filename_lower or "rh_reload_empty" in filename_lower or "rh_swim_uw_idle" in filename_lower

    if is_ads or is_add:
        cmds.select("%s:tag_view" % default_namespace, "%s:tag_torso" % default_namespace)

    elif is_dwl:
        cmds.select("%s:tag_cambone" % default_namespace, "%s:j_shoulder_le" % default_namespace, "%s:tag_weapon_left" % default_namespace, hierarchy=True)
        cmds.select("%s:tag_torso" % default_namespace, add=True)

    elif is_dwr:
        cmds.select("%s:tag_cambone" % default_namespace, "%s:j_shoulder_ri" % default_namespace, "%s:tag_weapon_right" % default_namespace, hierarchy=True)
        cmds.select("%s:tag_torso" % default_namespace, add=True)

    else:
        cmds.select("%s:tag_torso" % default_namespace, "%s:tag_cambone" % default_namespace, hierarchy=True)

    CoDMayaTools.SaveReminder = modified_save_reminder
    CoDMayaTools.RefreshXAnimWindow()

    CoDMayaTools.ReadNotetracks('xanim')

    textFieldName = CoDMayaTools.OBJECT_NAMES['xanim'][0] + "_SaveToField"
    cmds.textField(textFieldName, edit=True, text=output_file_path)

    CoDMayaTools.SetFrames('xanim')
    fpsFieldName = CoDMayaTools.OBJECT_NAMES['xanim'][0] + "_FPSField"
    cmds.intField(fpsFieldName, edit=True, value=30)

    qualityField = CoDMayaTools.OBJECT_NAMES['xanim'][0] + "_qualityField"
    cmds.intField(qualityField, edit=True, value=0)



    original_show_window = cmds.showWindow
    try:
        cmds.showWindow = lambda *args, **kwargs: None
        CoDMayaTools.GeneralWindow_ExportSelected('xanim', exportingMultiple=False)
    finally:
        castplugin.utilityClearAnimation()
        CoDMayaTools.ClearNotes('xanim')
        cmds.delete('CastNotetracks')
        cmds.showWindow = original_show_window
        CoDMayaTools.SaveReminder = original_save_reminder


def show_about_dialog(*args):
    if cmds.window("manyanimsAboutWindow", exists=True):
        cmds.deleteUI("manyanimsAboutWindow")

    try:
        if cmds.windowPref("manyanimsAboutWindow", exists=True):
            cmds.windowPref("manyanimsAboutWindow", remove=True)
    except:
        pass

    # Create window with fixed size and close button only
    window = cmds.window("manyanimsAboutWindow", title="About ManyAnims", sizeable=False, minimizeButton=False, maximizeButton=False)

    form = cmds.formLayout()

    # Title section
    title_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(label="ManyAnims for Maya", font="boldLabelFont", align="center")
    cmds.text(label="Batch animation exporter for Black Ops 3", align="center")
    cmds.text(label="Original script created by elfenliedtopfan5 for Sloth", align="center")
    cmds.text(label="Modified by Cinnamon(CinnaDev)", align="center")

    cmds.separator(style="in", height=10)
    cmds.setParent(form)

    # Changelog section
    frame = cmds.frameLayout(label="ChangeLog:", collapsable=False, borderStyle="etchedIn", marginWidth=10, marginHeight=10)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    cmds.text(label="v1 (Fork)", align="left")
    cmds.setParent("..")  # columnLayout
    cmds.setParent("..")  # frameLayout

    # Spacer and OK button
    bottom_sep = cmds.separator(style="in", height=10)
    button_row = cmds.rowLayout(numberOfColumns=1, height=40, adjustableColumn=1)
    cmds.button(label="OK", height=30, width=100, command=lambda x: cmds.deleteUI("manyanimsAboutWindow"))
    cmds.setParent(form)

    # Attach layout elements
    cmds.formLayout(form, edit=True,
        attachForm=[
            (title_col, 'top', 10), (title_col, 'left', 10), (title_col, 'right', 10),
            (frame, 'left', 10), (frame, 'right', 10),
            (bottom_sep, 'left', 10), (bottom_sep, 'right', 10),
            (button_row, 'left', 0), (button_row, 'right', 0), (button_row, 'bottom', 10)
        ],
        attachControl=[
            (frame, 'top', 10, title_col),
            (bottom_sep, 'top', 10, frame),
            (button_row, 'top', 10, bottom_sep)
        ]
    )

    # Show and fix window size
    cmds.showWindow(window)
    cmds.window(window, edit=True, widthHeight=(400, 220))

def open_namespace_dialog(*args):
    global default_namespace
    result = cmds.promptDialog(
        title="Set Namespace",
        message="Enter Default Namespace:",
        button=["OK", "Cancel"],
        defaultButton="OK",
        cancelButton="Cancel",
        dismissString="Cancel",
        text=default_namespace
    )
    if result == "OK":
        default_namespace = cmds.promptDialog(query=True, text=True)
        print("[ManyAnims] Namespace set to: %s" % default_namespace)

def create_menu():
    global export_button

    if cmds.menu("manyAnimsMenu", exists=True):
        cmds.deleteUI("manyAnimsMenu", menu=True)

    cmds.menu("manyAnimsMenu", label="ManyAnims", parent="MayaWindow")
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Select Animations", command=select_anim_files_dialog)
    cmds.menuItem(label="Export Path", command=set_export_path)
    cmds.menuItem(divider=True)
    export_button = cmds.menuItem(label="Export", command=on_export)
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Set Namespace...", command=open_namespace_dialog)
    cmds.menuItem(divider=True)

    cmds.setParent("manyAnimsMenu", menu=True)
    cmds.menuItem(label="About", command=show_about_dialog)

    toggle_ui_elements(False)

create_menu()
