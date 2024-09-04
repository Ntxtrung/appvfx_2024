import nuke
import nukescripts

from createWrite import MetadataPanel

def initialize_metadata_panel():
    panel = MetadataPanel()

    panel.client_enum.setValues(list(panel.client_tasks.keys()))
    metadata_node = nuke.toNode("metadata_storage")
    if metadata_node:
        panel.update_filename_enum()
        panel.update_info()
        panel.update_path_and_shot_name()
        panel.set_delivery_path()
        panel.update_info_metadata()

    return panel.addToPane()


nuke.addOnScriptLoad(initialize_metadata_panel)
# Register the panel in Nuke
nukescripts.registerPanel('com.example.MetadataPanel', initialize_metadata_panel)

# Add the panel to the Nuke menu
nuke.menu("Pane").addCommand("PAINT Tools", initialize_metadata_panel)

