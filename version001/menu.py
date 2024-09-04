import nuke
import clipboardCore

menu = nuke.menu("Nuke")
paint =  menu.addMenu("Paint")
paint.addCommand("QC", "clipboardCore.start()")