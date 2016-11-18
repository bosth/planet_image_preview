# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PlanetImagePreview
                                 A QGIS plugin
 Loads Planet imagery over a location
                             -------------------
        begin                : 2016-11-18
        copyright            : (C) 2016 by Benjamin Trigona-Harany
        email                : benjamin@planet.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load PlanetImagePreview class from file PlanetImagePreview.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .planet_image_preview import PlanetImagePreview
    return PlanetImagePreview(iface)
