# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PlanetImagePreview
                                 A QGIS plugin
 Loads Planet imagery over a location
                              -------------------
        begin                : 2016-11-18
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Benjamin Trigona-Harany
        email                : benjamin@planet.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QObject, SIGNAL
from PyQt4.QtGui import QAction, QIcon, QActionGroup, QWidgetAction, QInputDialog
# Initialize Qt resources from file resources.py
import resources
import os.path
from qgis.core import QgsRasterLayer, QgsMapLayerRegistry, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.gui import QgsMapToolEmitPoint, QgsVertexMarker
from requests import get
import json


class PlanetImagePreview:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'PlanetImagePreview_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Planet Image Preview')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'PlanetImagePreview')
        self.toolbar.setObjectName(u'PlanetImagePreview')

        self.canvas = self.iface.mapCanvas()
        self.api_key = None
        self.marker = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('PlanetImagePreview', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        checkable=False,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param checkable: Flag indicating whether the action can be toggled
            on or off.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        self.layer = None

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.clickTool = QgsMapToolEmitPoint(self.canvas)

        self.findAction = self.add_action(
            ':/plugins/PlanetImagePreview/icon_find.png',
            text=self.tr(u'Find Planet scene'),
            callback=self.run_find,
            checkable=True,
            parent=self.iface.mainWindow())

        self.prevAction = self.add_action(
            ':/plugins/PlanetImagePreview/icon_prev.png',
            text=self.tr(u'Older image'),
            callback=self.run_prev,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        self.nextAction = self.add_action(
            ':/plugins/PlanetImagePreview/icon_next.png',
            text=self.tr(u'Newer image'),
            callback=self.run_next,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        actionList = self.iface.mapNavToolToolBar().actions()
        tmpActionList = self.iface.attributesToolBar().actions()

        for action in tmpActionList:
            if isinstance(action, QWidgetAction):
                actionList.extend(action.defaultWidget().actions())
            else:
                actionList.append(action)

        group = QActionGroup(self.iface.mainWindow())
        group.setExclusive(True)
        for action in actionList:
            group.addAction(action)
        group.addAction(self.findAction)

        result = QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        self.iface.removeToolBarIcon(self.findAction)
        self.iface.removeToolBarIcon(self.nextAction)
        self.iface.removeToolBarIcon(self.prevAction)
        if not self.marker is None:
            self.canvas.scene().removeItem(self.marker)
        del self.toolbar


    def run_find(self):
        if not self.api_key:
            settings = QSettings()
            self.api_key = settings.value('/PlanetImagePreview/apikey', type=str)
            if not self.api_key:
                self.get_api_key()

        self.canvas.setMapTool(self.clickTool)

    def run_prev(self):
        idx = self.scene_idx + 1
        if idx < len(self.scenes):
            self.scene_idx = idx
            self.set_scene()
        self.set_action_toggle()

    def run_next(self):
        idx = self.scene_idx
        if idx != 0:
            self.scene_idx = idx - 1
            self.set_scene()
        self.set_action_toggle()

    def set_action_toggle(self):
        idx = self.scene_idx
        num = len(self.scenes)

        if num <= 1:
            self.nextAction.setEnabled(False)
            self.prevAction.setEnabled(False)
            return

        if idx == 0:
            self.nextAction.setEnabled(False)
            self.prevAction.setEnabled(True)
            return

        if idx == num - 1:
            self.nextAction.setEnabled(True)
            self.prevAction.setEnabled(False)
            return

        self.nextAction.setEnabled(True)
        self.prevAction.setEnabled(True)

    def handleMouseDown(self, point, button):
        if not self.marker is None:
            self.canvas.scene().removeItem(self.marker)
        srcCRS = self.canvas.mapSettings().destinationCrs()
        dstCRS = QgsCoordinateReferenceSystem(4326)
        xform = QgsCoordinateTransform(srcCRS, dstCRS)
        geo_point = xform.transform(point)
        self.lat = geo_point.x()
        self.lon = geo_point.y()

        region = 'POINT({} {})'.format(self.lat, self.lon)
        url = 'https://api.planet.com/v0/scenes/ortho?count=100&intersects=%s' % region
        response = get(url, auth=(self.api_key,''))
        if response.status_code == 401:
            self.get_api_key()
        elif response.status_code == 200:
            self.scenes = [scene['id'] for scene in json.loads(response.text, parse_float=str)['features']]
            if self.scenes:
                self.scene_idx = 0
                self.set_scene()
            self.set_action_toggle()

        self.marker = QgsVertexMarker(self.canvas)
        self.marker.setCenter(point)
        self.marker.setIconType(QgsVertexMarker.ICON_X )
        self.marker.setPenWidth(4)

    def set_scene(self):
        scene_id = self.scenes[self.scene_idx]
        url = "https://tiles.planet.com/v0/scenes/ortho/%s/{z}/{x}/{y}.png?api_key=%s" % (scene_id, self.api_key)
        url = url.replace('{', '%7B')
        url = url.replace('}', '%7D')
        url = url.replace('=', '%3D')
        name = '%s [%d/%d]' % (scene_id, self.scene_idx + 1, len(self.scenes))
        layer = QgsRasterLayer("crs=EPSG:3857&format=&type=xyz&url=%s" % url, name, "wms")
        QgsMapLayerRegistry.instance().addMapLayer(layer)
        try:
            if self.layer:
                QgsMapLayerRegistry.instance().removeMapLayer(self.layer)
        except RuntimeError:
            pass
        self.layer = layer

    def get_api_key(self):
        text, ok = QInputDialog.getText(None, 'Input Dialog', 'Planet API Key:')
        if ok:
            settings = QSettings()
            settings.setValue('/PlanetImagePreview/apikey', text)
            self.api_key = text
