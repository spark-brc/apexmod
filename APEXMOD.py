# -*- coding: utf-8 -*-
"""
/***************************************************************************
 APEXMOD
                                 A QGIS plugin
 This plugin helps link APEX with MODFLOW 
 and displays the result of APEX-MODFLOW simulation
 -------------------
        begin                : 2020-08-02  -- recent updated: 2020-09-03
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Seonggyu
        email                : seonggyu.park@brc.tamus.edu
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
from __future__ import absolute_import

# installation routine with acknowledgements to freewat
from builtins import str
from builtins import range
from builtins import object

# APEXMOD with implemented 3rd party modules
# from .install import installer as inst
# inst.check_install()

from qgis.PyQt.QtCore import (
                    QSettings, QTranslator, qVersion,
                    QCoreApplication, QFileInfo, QVariant
)
from qgis.PyQt import QtCore, QtGui, QtSql
from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery
from qgis.core import (
                    QgsVectorLayer, QgsField, QgsFeatureIterator, QgsProject,
                    QgsRasterLayer, QgsLayerTreeLayer, QgsProcessingFeedback
)

# QgsMapLayerRegistry: Its functionality has been moved to QgsProject.
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
                QAction, QDialog, QFormLayout, QMessageBox,
                QFileDialog, QSizePolicy
)

# Initialize Qt resources from file resources.py
from . import resources
# import resources_rc

# Import the code for the dialog
from .APEXMOD_dialog import APEXMODDialog
from .dialogs import createMFmodel_dialog
from .dialogs.createMFmodel_dialog import createMFmodelDialog # from folder.file import class
from .dialogs import help_dialog

from .dialogs import create_rt3d_dlg
from .dialogs import create_salt_dlg


# import sub functions from pyfolder -----------------------------------#
from .pyfolder import db_functions
from .pyfolder import runSim_link
from .pyfolder import modflow_functions
from .pyfolder import linking_process
from .pyfolder import post_i_cha
from .pyfolder import post_ii_wt
from .pyfolder import post_iii_rch
from .pyfolder import post_iv_gwsw
from .pyfolder import post_v_wb
from .pyfolder import post_vi_head
from .pyfolder import post_vii_nitrate
from .pyfolder import post_viii_salt
from .pyfolder import post_ix_solute_hyd
from .pyfolder import cvt_plotsToVideo
from .pyfolder import retrieve_ProjHistory
from .pyfolder import config_sets
from .pyfolder import load_inputs
from .pyfolder import write_rt3d
# from .pyfolder import apexmod_utils

# ----------------------------------------------------------------------#
import time
from datetime import datetime
import distutils.dir_util
import os
import os.path
import glob
import posixpath
import ntpath
import shutil
import processing

# import matplotlib.pyplot as plt
# import matplotlib.animation as animation
# import matplotlib.dates as mdates
# import numpy as np
# import pandas as pd
# from matplotlib import style
# plt.style.use('dark_background')


class APEXMOD(object):
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
            'APEXMOD_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&APEXMOD')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'&APEXMOD')
        self.toolbar.setObjectName(u'&APEXMOD')

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
        return QCoreApplication.translate('&APEXMOD', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
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

        # Create the dialog (after translation) and keep reference
        self.dlg = APEXMODDialog()

        icon = QIcon(':/APEXMOD/pics/am_icon.png')
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/APEXMOD/pics/am_icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())
        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&&APEXMOD'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # self.dlg.comboBox1.clicked.connect(self.selectChartType)
        # NOTE: 1st Tab
        self.dlg.pushButton_newproject.clicked.connect(self.newProject)
        self.dlg.pushButton_TxtInOut.clicked.connect(self.load_apex_model)

        # NOTE: 2nd Tab
        # import org_shps
        self.dlg.pushButton_subbasin_shapefile.clicked.connect(self.load_sub)
        self.dlg.pushButton_river_shapefile.clicked.connect(self.load_riv)
        self.dlg.pushButton_existingproject.clicked.connect(self.existingProject)

        # MODFLOW files
        self.dlg.pushButton_MODFLOWfile.clicked.connect(self.load_mf_model)
        self.dlg.pushButton_checkMF.clicked.connect(self.checkMF)
        
        # NOTE: APEX-MODFLOW creating linkagefiles included in run subroutine
        # self.dlg.pushButton_create_linkfiles.clicked.connect(self.createLinkFiles)
        self.dlg.checkBox_filesPrepared.toggled.connect(self.activate_execute_linking)        

        # Second Tab
        self.dlg.groupBox_threshold.toggled.connect(self.thres_dhru)
        self.dlg.horizontalSlider_ol_area.valueChanged.connect(self.thres_dhru_value)

        self.dlg.pushButton_mf_obs_points.clicked.connect(self.use_obs_points)
        self.dlg.pushButton_mf_obs_shapefile.clicked.connect(self.mf_obs_shapefile)
        self.dlg.pushButton_export_modflow_obs.clicked.connect(self.export_mf_obs)
        self.dlg.pushButton_createMFmodel.clicked.connect(self.showCreateMFmodel_dialog)
        self.dlg.pushButton_help.clicked.connect(self.showHelp_dialog)
        self.dlg.pushButton_MF_grid_shapefile.clicked.connect(self.import_mf_grid)
        # River
        self.dlg.pushButton_create_rivs.clicked.connect(self.create_rivs)
        self.dlg.pushButton_overwrite_RIVpac.clicked.connect(self.owRivPac)

        # Open rt3d ui
        self.dlg.pushButton_open_rt3d_ui.clicked.connect(self.openRT3Dui)
        self.dlg.pushButton_open_salt_ui.clicked.connect(self.open_salt_ui)

        # NOTE: 3rd Tab
        self.dlg.checkBox_mf_obs.toggled.connect(self.check_mf_obs)
        self.dlg.radioButton_irrig_act.toggled.connect(self.irr_mf)
        self.dlg.radioButton_irrig_swat_act.toggled.connect(self.irr_swat)
        # self.dlg.radioButton_irrig_inact.toggled.connect(self.irr_mf)
        # self.dlg.radioButton_irrig_swat_inact.toggled.connect(self.irr_swat)
        self.dlg.pushButton_irrig_mf.clicked.connect(self.link_irrig_mf)
        self.dlg.pushButton_irrig_mf_create.clicked.connect(self.create_irrig_mf)
        self.dlg.radioButton_drain_act.toggled.connect(self.link_drain)
        self.dlg.radioButton_ActRT3D.toggled.connect(self.act_rt3d)
        self.dlg.pushButton_dtoch_create.clicked.connect(self.create_drain2sub)
        self.dlg.pushButton_irrig_swat_write.clicked.connect(self.write_irrig_swat)
        self.dlg.pushButton_irrig_swat_pts.clicked.connect(self.use_irrig_swat_pts)
        self.dlg.pushButton_irrig_swat_grids.clicked.connect(self.irrig_swat_selected)
        self.dlg.radioButton_gw_delay_single.toggled.connect(self.gwd_selection)
        self.dlg.radioButton_gw_delay_multi.toggled.connect(self.gwd_selection)
        self.dlg.pushButton_gw_delay_multi.clicked.connect(self.gw_delay)

        ### fourthTab
        # self.dlg.comboBox_cha_time.clear()
        # self.dlg.comboBox_cha_time.addItems(['Daily', 'Monthly', 'Annual'])
        # self.dlg.comboBox_SD_plotType.clear()
        # self.dlg.comboBox_SD_plotType.addItems(['Static Plot', 'Dynamic Plot'])
        self.dlg.comboBox_hh_time.clear()
        self.dlg.comboBox_hh_time.addItems(['Daily', 'Monthly', 'Annual'])
        # self.dlg.comboBox_hh_plotType.clear()
        # self.dlg.comboBox_hh_plotType.addItems(['Static Plot', 'Dynamic Plot'])
        self.dlg.pushButton_create_apexmf_link.clicked.connect(self.create_apexmf_link)

        self.dlg.comboBox_colormaps.clear()
        self.dlg.comboBox_colormaps.addItems(
            ['gist_rainbow', 'rainbow', 'jet', 'spring', 'summer', 'autumn',
                'winter', 'cool', 'gray', 'Spectral'])

        # NOTE: 4th Tab
        self.dlg.horizontalSlider_cha_start_year.valueChanged.connect(self.cha_year_label)
        self.dlg.pushButton_plot_cha.clicked.connect(self.plot_cha)
        self.dlg.pushButton_plot_wt.clicked.connect(self.plot_wt)
        self.dlg.pushButton_plot_gwsw.clicked.connect(self.plot_gwsw)
        self.dlg.groupBox_cha_obd.toggled.connect(self.activate_cha_obd)
        self.dlg.comboBox_cha_obd_files.currentIndexChanged.connect(self.get_cha_obd_gages)
        # === Export data to file
        self.dlg.pushButton_export_cha.clicked.connect(self.export_cha)
        self.dlg.pushButton_export_wt.clicked.connect(self.export_wt)
        ## Export mf_recharge to shapefile
        self.dlg.radioButton_mf_results_d.toggled.connect(self.import_mf_dates)
        self.dlg.radioButton_mf_results_m.toggled.connect(self.import_mf_dates)
        self.dlg.radioButton_mf_results_y.toggled.connect(self.import_mf_dates)
        self.dlg.checkBox_head.toggled.connect(self.import_mf_dates)
        self.dlg.pushButton_export_mf_results.clicked.connect(self.export_mf_results)

        # 4th Read GWSW
        self.dlg.groupBox_gwsw.toggled.connect(self.activate_gwsw)
        self.dlg.radioButton_gwsw_day.toggled.connect(self.import_mf_gwsw_dates)
        self.dlg.radioButton_gwsw_month.toggled.connect(self.import_mf_gwsw_dates)
        self.dlg.radioButton_gwsw_year.toggled.connect(self.import_mf_gwsw_dates)
        self.dlg.checkBox_gwsw_yaxes.toggled.connect(self.readExtentSub)

        self.dlg.groupBox_gwsw.toggled.connect(self.cvt_plotsToVideo)
        self.dlg.checkBox_gwsw_toVideo.toggled.connect(self.cvt_plotsToVideo)
        self.dlg.pushButton_gwsw_autoplot.clicked.connect(self.ani)
        self.dlg.groupBox_gwsw.toggled.connect(self.create_gwsw_shp)
        self.dlg.checkBox_export_gwsw_shp.toggled.connect(self.create_gwsw_shp)

        # Export GWSW
        self.dlg.pushButton_gwsw_export.clicked.connect(self.export_gwsw)
        self.dlg.pushButton_export_gwsw.clicked.connect(self.export_gwswToShp)

        # == Read output.std
        self.dlg.groupBox_std.toggled.connect(self.std_time_option)

        self.dlg.radioButton_std_day.toggled.connect(self.import_std_dates)
        self.dlg.radioButton_std_month.toggled.connect(self.import_std_dates)
        self.dlg.radioButton_std_year.toggled.connect(self.import_std_dates)
        self.dlg.pushButton_std_plot.clicked.connect(self.plot_std)

        # Export output.std
        self.dlg.pushButton_std_export_wb.clicked.connect(self.export_wb)
        ##
        self.dlg.checkBox_wt_obd.toggled.connect(self.read_wtObd)
        # self.dlg.pushButton_refresh.clicked.connect(self.swat_analyze_subbasin)
        self.dlg.pushButton_createMF.clicked.connect(self.createMF)
        self.dlg.pushButton_execute_linking.clicked.connect(self.geoprocessing_prepared)
        self.dlg.checkBox_default_extent.toggled.connect(self.defaultExtent)
        self.dlg.groupBox_add_grid.toggled.connect(self.enable_grid_number)

        # From modflow_functions


        # ---------------------------------------------------------------------------------------------
        self.dlg.tabWidget.currentChanged.connect(self.check_outputs)
        self.dlg.tabWidget.currentChanged.connect(self.check_outputs_rt3d)
        self.dlg.tabWidget.currentChanged.connect(self.define_sim_period)
        # ---------------------------------------------------------------------------------------------
        # NOTE: 5th tab for RT3D results --------------------------------------------------------------------
        ## Export mf_nitrate to shapefile
        self.dlg.horizontalSlider_solute_start_year.valueChanged.connect(self.solute_year_label)
        
        self.dlg.radioButton_rt3d_d.toggled.connect(self.import_rt3d_salt_dates)
        self.dlg.radioButton_rt3d_m.toggled.connect(self.import_rt3d_salt_dates)
        self.dlg.radioButton_rt3d_y.toggled.connect(self.import_rt3d_salt_dates)
        self.dlg.radioButton_rt3d_d.toggled.connect(self.create_rt3d_salt_shps)
        self.dlg.radioButton_rt3d_m.toggled.connect(self.create_rt3d_salt_shps)
        self.dlg.radioButton_rt3d_y.toggled.connect(self.create_rt3d_salt_shps)        
        self.dlg.comboBox_solutes.currentIndexChanged.connect(self.import_rt3d_salt_dates)
        self.dlg.comboBox_solutes.currentIndexChanged.connect(self.create_rt3d_salt_shps)

        # self.dlg.checkBox_nitrate.toggled.connect(self.import_mf_dates)
        self.dlg.pushButton_solute_plot_show.clicked.connect(self.solute_plot)
        self.dlg.pushButton_solute_df_export.clicked.connect(self.export_solute_df)
        self.dlg.groupBox_export_solutes.toggled.connect(self.get_compNames)
        self.dlg.pushButton_export_rt_results.clicked.connect(self.export_solute_results)
        self.dlg.mGroupBox_rt_avg.toggled.connect(self.create_avg_m_shps)
        self.dlg.mGroupBox_cvt_vtr.toggled.connect(self.read_vector_maps)
        self.dlg.pushButton_cvt_vtr.clicked.connect(self.cvt_vtr)

        # 5th tab for Salt
        self.dlg.horizontalSlider_salt_start_year.valueChanged.connect(self.salt_year_label)
        self.dlg.groupBox_salt_channel.toggled.connect(self.activate_salt_channel)
        self.dlg.pushButton_salt_plot.clicked.connect(self.salt_ions_plot)
        self.dlg.pushButton_salt_export.clicked.connect(self.salt_export)

        self.dlg.groupBox_salt_obd.toggled.connect(self.activate_salt_obd)
        self.dlg.comboBox_salt_obd_files.currentIndexChanged.connect(self.get_salt_obd_gages)

        # ---------------------------------------------------------------------------------------------
        # Run
        self.dlg.pushButton_run_apexmf_model.clicked.connect(self.run_apexmf_model)

        # Set tab enable
        for i in range(1, 6):
            self.dlg.tabWidget.setTabEnabled(i, False)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    # NOTE: functions start

    def activate_execute_linking(self):
        if self.dlg.checkBox_filesPrepared.isChecked():
            self.dlg.pushButton_execute_linking.setEnabled(False)
        else:
            self.dlg.pushButton_execute_linking.setEnabled(True)

    def test111(self):
        post_i_cha.test111(self)

    def ani(self):
        post_iv_gwsw.plot_gwsw_ani(self)
        if self.dlg.checkBox_gwsw_toVideo.isChecked():
            cvt_plotsToVideo.cvt_plotsToVideo(self)


    def check_mf_obs(self):
        APEXMOD_path_dict = self.dirs_and_paths()
        wd = APEXMOD_path_dict['MODFLOW']
        if self.dlg.checkBox_mf_obs.isChecked():
            self.dlg.groupBox_plot_wt.setEnabled(True)
            try:
                # wd = APEXMOD_path_dict['apexmf_model']
                mf_obs = open(os.path.join(wd, "modflow.obs"), "r")
            except:
                msgBox = QMessageBox()
                msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
                msgBox.setWindowTitle("No 'modflow.obs' file found!")
                msgBox.setText("Please, create 'modflow.obs' file first!")
                msgBox.exec_()
                self.dlg.checkBox_mf_obs.setChecked(0)
                self.dlg.groupBox_plot_wt.setEnabled(False)
        else:
            self.dlg.checkBox_mf_obs.setChecked(0)
            self.dlg.groupBox_plot_wt.setEnabled(False)

    def define_sim_period(self):
        import datetime
        APEXMOD_path_dict = self.dirs_and_paths()
        wd = APEXMOD_path_dict['apexmf_model']
        if os.path.isfile(os.path.join(wd, "APEXCONT.DAT")):
            with open(os.path.join(wd, 'APEXCONT.DAT'), "r") as f:
                data = [x.strip().split() for x in f if x.strip()]
            numyr = int(data[0][0])
            styr = int(data[0][1])
            stmon = int(data[0][2])
            stday = int(data[0][3])
            ptcode = int(data[0][4])
            edyr = styr + numyr -1
            stdate = datetime.datetime(styr, stmon, 1) + datetime.timedelta(stday - 1)
            eddate = datetime.datetime(edyr, 12, 31) 
            duration = (eddate - stdate).days

            ##### 
            start_month = stdate.strftime("%b")
            start_day = stdate.strftime("%d")
            start_year = stdate.strftime("%Y")
            end_month = eddate.strftime("%b")
            end_day = eddate.strftime("%d")
            end_year = eddate.strftime("%Y")

            # Put dates into the gui
            self.dlg.lineEdit_start_m.setText(start_month)
            self.dlg.lineEdit_start_d.setText(start_day)
            self.dlg.lineEdit_start_y.setText(start_year)
            self.dlg.lineEdit_end_m.setText(end_month)
            self.dlg.lineEdit_end_d.setText(end_day)
            self.dlg.lineEdit_end_y.setText(end_year)
            self.dlg.lineEdit_duration.setText(str(duration))

            self.dlg.lineEdit_nyskip.setText(str(0))

            # Check IPRINT option
            if ptcode == 3 or ptcode == 4 or ptcode == 5:  # month
                self.dlg.comboBox_cha_time.clear()
                self.dlg.comboBox_cha_time.addItems(['Monthly', 'Annual'])
                self.dlg.radioButton_month.setChecked(1)
                self.dlg.radioButton_month.setEnabled(True)
                self.dlg.radioButton_day.setEnabled(False)
                self.dlg.radioButton_year.setEnabled(False)
            elif ptcode == 6 or ptcode == 7 or ptcode == 8 or ptcode == 9:
                self.dlg.comboBox_cha_time.clear()
                self.dlg.comboBox_cha_time.addItems(['Daily', 'Monthly', 'Annual'])
                self.dlg.radioButton_day.setChecked(1)
                self.dlg.radioButton_day.setEnabled(True)
                self.dlg.radioButton_month.setEnabled(False)
                self.dlg.radioButton_year.setEnabled(False)
            elif ptcode == 0 or ptcode == 1 or ptcode == 2:
                self.dlg.comboBox_cha_time.clear()
                self.dlg.comboBox_cha_time.addItems(['Annual'])
                self.dlg.radioButton_year.setChecked(1)
                self.dlg.radioButton_year.setEnabled(True)
                self.dlg.radioButton_day.setEnabled(False)
                self.dlg.radioButton_month.setEnabled(False)
            return stdate, eddate


    ### Fourth tab
    def read_strObd(self):
        post_i_cha.read_strObd(self)

    def read_wtObd(self):
        post_ii_wt.read_wtObd(self)

    def export_mf_results(self):
        if self.dlg.checkBox_recharge.isChecked():
            post_iii_rch.export_mf_recharge(self)
        elif self.dlg.checkBox_head.isChecked():
            post_vi_head.export_mf_head(self)
        # elif (
        #         self.dlg.comboBox_solutes.currentText() == 'NO3 (Nitrate)' and 
        #         not self.dlg.mGroupBox_rt_avg.isChecked()):
        #     post_vii_nitrate.export_rt_cno3(self)
        # elif (
        #         self.dlg.comboBox_solutes.currentText() == 'NO3 (Nitrate)' and 
        #         self.dlg.mGroupBox_rt_avg.isChecked()):
        #     self.export_rt_cno3_avg_m()

    def import_mf_dates(self):
        if self.dlg.checkBox_recharge.isChecked():
            self.dlg.radioButton_mf_results_d.setEnabled(True)
            post_iii_rch.read_mf_recharge_dates(self)
        elif self.dlg.checkBox_head.isChecked():
            post_vi_head.read_mf_nOflayers(self)
            self.dlg.radioButton_mf_results_d.setEnabled(False)
            post_vi_head.read_mf_head_dates(self)
        elif self.dlg.comboBox_solutes.currentText() == 'NO3 (Nitrate)':
            post_vii_nitrate.read_mf_nOflayers(self)
            post_vii_nitrate.read_mf_nitrate_dates(self)


    def import_mf_gwsw_dates(self):
        post_iv_gwsw.read_mf_gwsw_dates(self)

    def activate_gwsw(self):
        post_iv_gwsw.dissolvedSub(self)
        post_iv_gwsw.create_sm_riv(self)

    def std_time_option(self):
        post_v_wb.read_dws_files(self)
        if self.dlg.radioButton_day.isChecked():
            self.dlg.radioButton_std_day.setEnabled(True)
            self.dlg.radioButton_std_month.setEnabled(True)
            self.dlg.radioButton_std_year.setEnabled(True)
        elif self.dlg.radioButton_month.isChecked():
            self.dlg.radioButton_std_day.setEnabled(False)
            self.dlg.radioButton_std_month.setEnabled(True)
            self.dlg.radioButton_std_year.setEnabled(True)
        elif self.dlg.radioButton_year.isChecked():
            self.dlg.radioButton_std_day.setEnabled(False)
            self.dlg.radioButton_std_month.setEnabled(False)
            self.dlg.radioButton_std_year.setEnabled(True)
        else:
            self.dlg.radioButton_std_day.setEnabled(False)
            self.dlg.radioButton_std_month.setEnabled(False)
            self.dlg.radioButton_std_year.setEnabled(False)

    def import_std_dates(self):
        post_v_wb.read_std_dates(self)

    def readExtentSub(self):
        if self.dlg.checkBox_gwsw_yaxes.isChecked():
            self.dlg.lineEdit_gwsw_y_min.setEnabled(True)
            self.dlg.lineEdit_gwsw_y_max.setEnabled(True)
            post_iv_gwsw.readExtentSub(self)
        else:
            self.dlg.lineEdit_gwsw_y_min.setEnabled(False)
            self.dlg.lineEdit_gwsw_y_max.setEnabled(False)

    def cvt_plotsToVideo(self):
        self.dlg.groupBox_10.setEnabled(True)
        self.dlg.checkBox_gwsw_toVideo.setEnabled(True)
        self.dlg.lineEdit_gwsw_dpi.setEnabled(True)
        self.dlg.lineEdit_gwsw_fps.setEnabled(True)
        self.dlg.pushButton_gwsw_autoplot.setEnabled(True)
        # if self.dlg.checkBox_gwsw_toVideo.isChecked():
        #     self.dlg.lineEdit_gwsw_dpi.setEnabled(True)
        #     self.dlg.lineEdit_gwsw_fps.setEnabled(True)
        # else:
        #     self.dlg.lineEdit_gwsw_dpi.setEnabled(False)
        #     self.dlg.lineEdit_gwsw_fps.setEnabled(False)


    #### From modflow_functions --------------------------------------------------------------#
    # Create "modflow.obs" file

    # Use Observed well point shapefile
    def use_obs_points(self):
        modflow_functions.use_obs_points(self)
        modflow_functions.select_obs_grids(self)
        modflow_functions.create_modflow_obs(self)
        # self.showCreateMFmodel_dialog()
        msgBox = QMessageBox()
        # msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"hi", "",
        #   buttons =QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setIconPixmap(QtGui.QPixmap(':/APEXMOD/pics/modflow_obs.png'))
        msgBox.setMaximumSize(1000, 200)  # resize not working
        msgBox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred) # resize not working
        msgBox.setWindowTitle("Hello?")
        #msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        # msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
        # msgBox.setText("There is no 'sub' shapefile!")
        msgBox.exec_()


    # Select features by manual
    def mf_obs_shapefile(self):
        modflow_functions.mf_obs_shapefile(self)
        modflow_functions.create_modflow_obs(self)

        #self.showCreateMFmodel_dialog()
        msgBox = QMessageBox()
        # msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"hi", "",
        #   buttons =QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setIconPixmap(QtGui.QPixmap(':/APEXMOD/pics/modflow_obs.png'))
        msgBox.setMaximumSize(1000, 200) # resize not working
        msgBox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred) # resize not working
        msgBox.setWindowTitle("Hello?")
        #msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        # msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
        # msgBox.setText("There is no 'sub' shapefile!")
        msgBox.exec_()

    def export_mf_obs(self):
        modflow_functions.export_modflow_obs(self)
        self.dlg.groupBox_plot_wt.setEnabled(True)
        post_ii_wt.read_grid_id(self)
        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setMaximumSize(1000, 200) # resize not working
        msgBox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred) # resize not working
        msgBox.setWindowTitle("Created!")
        msgBox.setText("The 'modflow.obs' file is created in your APEX-MODFLOW folder!")
        msgBox.exec_()

    def import_mf_grid(self):
        # import modflow grid
        self.dlg.progressBar_sm_link.setValue(0)
        load_inputs.import_mf_grid(self)
        self.dlg.progressBar_sm_link.setValue(20)
        QCoreApplication.processEvents()
        
        # create grid_id
        modflow_functions.create_grid_id(self)
        self.dlg.progressBar_sm_link.setValue(40)
        QCoreApplication.processEvents()

        # create additioanl information
        modflow_functions.create_row(self)
        QCoreApplication.processEvents()
        self.dlg.progressBar_sm_link.setValue(60)        

        modflow_functions.create_col(self)
        self.dlg.progressBar_sm_link.setValue(80)
        QCoreApplication.processEvents()

        modflow_functions.create_elev_mf(self)
        self.dlg.progressBar_sm_link.setValue(100)
        QCoreApplication.processEvents()

        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setWindowTitle("Imported!")
        msgBox.setText("'mf_grid' shapefile has been imported!")
        msgBox.exec_()

    def create_rivs(self):
        if self.dlg.radioButton_mf_riv1.isChecked():
            # linking_process.deleting_river_grid(self)
            modflow_functions.mf_riv1(self)
            modflow_functions.create_riv_info(self)
            linking_process.river_grid(self)
            linking_process.river_grid_delete_NULL(self)
            linking_process.rgrid_len(self)
            linking_process.delete_river_grid_with_threshold(self)
        elif self.dlg.radioButton_mf_riv2.isChecked():
            # linking_process.deleting_river_grid(self)            
            modflow_functions.mf_riv2(self)
            linking_process.river_grid(self)
            linking_process.river_grid_delete_NULL(self)
            linking_process.rgrid_len(self)
            linking_process.delete_river_grid_with_threshold(self)
            modflow_functions.rivInfoTo_mf_riv2(self)
            modflow_functions.riv_cond_delete_NULL(self)
            # modflow_functions.getElevfromDem_riv2(self)
        elif self.dlg.radioButton_mf_riv3.isChecked():
            # linking_process.deleting_river_grid(self)            
            modflow_functions.mf_riv3(self)
            linking_process.river_grid(self)
            linking_process.river_grid_delete_NULL(self)
            linking_process.rgrid_len(self)
            linking_process.delete_river_grid_with_threshold(self)
        linking_process.export_rgrid_len(self)
        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setWindowTitle("Identified!")
        msgBox.setText("River cells have been identified!")
        msgBox.exec_()

        self.riv_opt3_enable()
        self.dlg.pushButton_checkMF.setEnabled(True)

    # mf_options ----------------------------------------------------------------
    def mfOptionOn(self):
        if (
            #self.dlg.lineEdit_TxtInOut.text() and loading TxtInOut takes a time!
            self.dlg.lineEdit_subbasin_shapefile.text() and
            self.dlg.lineEdit_river_shapefile.text()
            ):
            self.dlg.groupBox_MF_options.setEnabled(True)
            self.dlg.lineEdit_MODFLOW.setEnabled(True)
            self.dlg.mf_option_1.setEnabled(True)
            self.dlg.mf_option_2.setEnabled(True)
            self.dlg.groupBox_river_cells.setEnabled(False)

            self.mf_options()
            self.riv_options() # Initiate riv_options enable    

        else:
            self.dlg.groupBox_MF_options.setEnabled(False)
            self.mf_options()

    def mf_model(self):
        if self.dlg.lineEdit_MODFLOW.text():
            self.dlg.mf_option_1.setEnabled(True)
            self.dlg.mf_option_2.setEnabled(True)
            self.dlg.mf_option_3.setEnabled(False)
            self.dlg.groupBox_river_cells.setEnabled(True)
            self.dlg.river_frame.setEnabled(False)
            self.dlg.radioButton_mf_riv3.setEnabled(False)
        else:
            self.dlg.mf_option_1.setEnabled(False)
            self.dlg.mf_option_2.setEnabled(False)
            self.dlg.mf_option_3.setEnabled(True)

    def mf_options(self):
        self.dlg.mf_option_1.toggled.connect(self.mf_option_1)
        self.dlg.mf_option_2.toggled.connect(self.mf_option_2)
        self.dlg.mf_option_3.toggled.connect(self.mf_option_3)

    def mf_option_1(self):
        if self.dlg.mf_option_1.isChecked():
            self.dlg.mf_option_2.setChecked(False)
            self.dlg.mf_option_2.setCollapsed(True)         
            self.dlg.mf_option_3.setChecked(False)
            self.dlg.mf_option_3.setCollapsed(True)     
        else:
            self.dlg.mf_option_1.setChecked(False)
            self.dlg.mf_option_1.setCollapsed(True)

    def mf_option_2(self):
        if self.dlg.mf_option_2.isChecked():
            self.dlg.groupBox_add_grid.setEnabled(True)
            self.dlg.mf_option_1.setChecked(False)
            self.dlg.mf_option_1.setCollapsed(True)
            self.dlg.mf_option_3.setChecked(False)
            self.dlg.mf_option_3.setCollapsed(True)
        else:
            self.dlg.mf_option_2.setChecked(False)
            self.dlg.mf_option_2.setCollapsed(True)

    def mf_option_3(self):
        if self.dlg.mf_option_3.isChecked():
            self.dlg.mf_option_1.setChecked(False)
            self.dlg.mf_option_1.setCollapsed(True)
            self.dlg.mf_option_2.setChecked(False)
            self.dlg.mf_option_2.setCollapsed(True)
        else:
            self.dlg.mf_option_3.setChecked(False)
            self.dlg.mf_option_3.setCollapsed(True)

    def enable_grid_number(self):
        if self.dlg.groupBox_add_grid.isChecked():
            self.dlg.label_col.setEnabled(True)
            self.dlg.label_row.setEnabled(True)
            self.dlg.line_add.setEnabled(True)
            self.dlg.spinBox_col.setEnabled(True)
            self.dlg.spinBox_row.setEnabled(True)
        else:
            self.dlg.label_col.setEnabled(False)
            self.dlg.label_row.setEnabled(False)
            self.dlg.line_add.setEnabled(False)
            self.dlg.spinBox_col.setEnabled(False)
            self.dlg.spinBox_row.setEnabled(False)            

    # river_options ----------------------------------------------------------------
    def riv_options(self):
        self.dlg.radioButton_mf_riv1.toggled.connect(self.riv_option_enable)
        self.dlg.radioButton_mf_riv2.toggled.connect(self.riv_option_enable)
        self.dlg.radioButton_mf_riv3.toggled.connect(self.riv_option_enable)

    def riv_option_enable(self):
        if self.dlg.radioButton_mf_riv2.isChecked() or self.dlg.radioButton_mf_riv3.isChecked():
            self.dlg.river_frame.setEnabled(True)
            self.dlg.checkBox_swat_riv.setEnabled(True)
        else:
            self.dlg.river_frame.setEnabled(False)
            self.dlg.checkBox_swat_riv.setEnabled(False)
            self.dlg.checkBox_mf_riv.setChecked(True)

    def riv_opt3_enable(self):
        requiredLayers = []
        for lyr in list(QgsProject.instance().mapLayers().values()):
            if lyr.name() == ("mf_riv1 (MODFLOW)"):
                requiredLayers.append(lyr.name())
            elif lyr.name() == ("mf_riv2 (MODFLOW)"):
                requiredLayers.append(lyr.name())
        if len(requiredLayers) == 2:
            self.dlg.radioButton_mf_riv3.setEnabled(True)
        else:
            self.dlg.radioButton_mf_riv3.setEnabled(False)

    def owRivPac(self):
        modflow_functions.overwriteRivPac(self)

    # NOTE: createmap.exe in APEX-MODFLOW
    # def createLinkFiles(self):
    #     linking_process.run_CreateSWATMF(self)
    #     linking_process.copylinkagefiles(self)
    #     msgBox = QMessageBox()
    #     msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
    #     msgBox.setWindowTitle("Exported!")
    #     msgBox.setText("Linkage files have been exported to your APEX-MODFLOW folder!")
    #     msgBox.exec_()
    #     self.dlg.tabWidget.setTabEnabled(2, True)
    # --------------------------------------------------------------------------

    # 3rd Tab - Configuration Setting -----------------------------------------
    def irr_mf(self):
        if self.dlg.radioButton_irrig_act.isChecked():
            self.dlg.irrigate_mf.setEnabled(True)
            self.dlg.irrigate_mf.setCollapsed(False)
            self.dlg.radioButton_irrig_swat_inact.setChecked(1)
            self.dlg.irrigate_swat.setEnabled(False)
            self.dlg.irrigate_swat.setCollapsed(True)
            config_sets.create_conv_runoff(self)
        else:
            self.dlg.irrigate_mf.setEnabled(False)
            self.dlg.irrigate_mf.setCollapsed(True)

    def irr_swat(self):
        if self.dlg.radioButton_irrig_swat_act.isChecked():
            self.dlg.irrigate_swat.setEnabled(True)
            self.dlg.irrigate_swat.setCollapsed(False)
            self.dlg.radioButton_irrig_inact.setChecked(True)
            self.dlg.irrigate_mf.setEnabled(False)
            self.dlg.irrigate_mf.setCollapsed(True)
            config_sets.create_irrig_swat_tree(self)
        else:
            self.dlg.irrigate_swat.setEnabled(False)
            self.dlg.irrigate_swat.setCollapsed(True)

    def link_irrig_mf(self):
        config_sets.link_irrig_mf(self)

    def create_irrig_mf(self):
        config_sets.create_irrig_mf(self)

    def link_drain(self):
        if self.dlg.radioButton_drain_act.isChecked():
            self.dlg.label_dtoch.setEnabled(True)
            self.dlg.pushButton_dtoch_create.setEnabled(True)
            config_sets.link_drain(self)
        else:
            self.dlg.label_dtoch.setEnabled(False)
            self.dlg.pushButton_dtoch_create.setEnabled(False)

    def act_rt3d(self):
        if self.dlg.radioButton_ActRT3D.isChecked():
            self.dlg.label_rt3d.setEnabled(True)
        else:
            self.dlg.label_rt3d.setEnabled(False)

    def create_drain2sub(self):
        config_sets.create_drain2sub(self)

    def write_irrig_swat(self):
        config_sets.write_irrig_swat(self)
        config_sets.modify_wel(self)

    def use_irrig_swat_pts(self):
        config_sets.use_irrig_swat_pts(self)
        config_sets.select_irrig_swat_grids(self)
        config_sets.link_irrig_swat(self)

    def irrig_swat_selected(self):
        config_sets.irrig_swat_selected(self)
        config_sets.link_irrig_swat(self)

    def gwd_selection(self):
        if self.dlg.radioButton_gw_delay_single.isChecked():
            self.dlg.spinBox_gw_delay_single.setEnabled(True)
            self.dlg.spinBox_gw_delay_multi.setEnabled(False)
            self.dlg.pushButton_gw_delay_multi.setEnabled(False)
        else:
            self.dlg.spinBox_gw_delay_single.setEnabled(False)
            self.dlg.spinBox_gw_delay_multi.setEnabled(True)
            self.dlg.pushButton_gw_delay_multi.setEnabled(True)            

    def gw_delay(self):
        config_sets.gw_delay(self)
    # --------------------------------------------------------------------------

    def existingProject(self):
        # Open an existing QGIS project.
        self.iface.actionOpenProject().trigger()
        # allow time for project to be opened
        time.sleep(2)
        proj = QgsProject.instance()

        if proj.fileName() == '':
            msgBox = QMessageBox()
            msgBox.setText("No project was opened")
            msgBox.exec_()
            self.dlg.raise_()
            # return
        else:
            # several database functions are activated
            #self.DB_Pull_Project()         
            time.sleep(2)

            # self.DB_CreateConnection()
            # self.DB_Pull_Project()

            db_functions.DB_CreateConnection(self)
            self.dirs_and_paths()

            smProjPath = proj.readPath("./")
            self.dlg.lineEdit_proj_path.setText(smProjPath)

            # self.check_SMfolder_and_files()
            self.test_table()
            self.DB_Pull_Project()
            self.dlg.tabWidget.setTabEnabled(1, True)
            retrieve_ProjHistory.retrieve_ProjHistory(self)

            self.mfOptionOn() # enable
            self.mf_model()
            self.riv_options()
            self.riv_option_enable()
            self.riv_opt3_enable()
            # db_functions.DB_Pull_Project(self)

            post_i_cha.read_sub_no(self)
            post_ii_wt.read_grid_id(self)
            retrieve_ProjHistory.wt_act(self)
            self.dlg.raise_()     
            # self.define_sim_period()  
            #enables the tabs for project configuration
            # self.tab_enable()

    def create_apexmf_link(self):
        runSim_link.write_apexmf_link(self)

    def defaultExtent(self):
        modflow_functions.defaultExtent(self)

    '''
    def defaultExtent(self, state):
        try:
            self.layer = QgsProject.instance().mapLayersByName("sub (APEX)")[0]
            provider = self.layer.dataProvider()

            if state == self.dlg.checkBox_default_extent.isChecked():
                extent = self.layer.extent()
                x_origin = extent.xMinimum()
                y_origin = extent.yMaximum()
                self.dlg.lineEdit_x_coordinate.setText(str(x_origin))
                self.dlg.lineEdit_y_coordinate.setText(str(y_origin))

        except:
            msgBox = QMessageBox()
            msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
            msgBox.setWindowTitle("What the FXXXX!")
            msgBox.setText("There is no 'sub' shapefile!")
            msgBox.exec_()
            self.dlg.checkBox_default_extent.setChecked(0)

    '''
    # def visualize_SD(self):
    #   selection = self.dlg.comboBox_cha_time.currentText()
    #   selection_plotType = self.dlg.comboBox_SD_plotType.currentText()
    #   # checked_streamObs = self.dlg.
    #   SM_output_rch_1.visualize_SD(self, selection, selection_plotType)

    # def MF_grid(self):
    #     x_origin = self.dlg.lineEdit_x_coordinate.text()
    #     y_origin = self.dlg.lineEdit_y_coordinate.text()

    #     modflow_functions.MF_grid(x_origin, y_origin)

    # NOTE: 4th tab cha file visualization

    def cha_year_label(self):
        current_year = self.dlg.horizontalSlider_cha_start_year.value()
        self.dlg.label_cha_year.setText(str(current_year))

    def plot_cha(self):
        if not self.dlg.groupBox_cha_obd.isChecked():
            post_i_cha.cha_plot(self)
        if self.dlg.groupBox_cha_obd.isChecked() and not self.dlg.checkBox_hydro_scatter.isChecked():
            post_i_cha.cha_sim_obd_plot(self)
        if self.dlg.groupBox_cha_obd.isChecked() and self.dlg.checkBox_hydro_scatter.isChecked():
            post_i_cha.cha_sim_obd_with_scatter(self)

        # # Daily output format given
        # if self.dlg.radioButton_day.isChecked() and (self.dlg.comboBox_cha_time.currentText() == "Daily"):
        #     post_i_cha.sd_plot_daily(self)
        # elif self.dlg.radioButton_day.isChecked() and (self.dlg.comboBox_cha_time.currentText() == "Monthly"):
        #     post_i_cha.sd_plot_monthly(self)            
        # elif self.dlg.radioButton_day.isChecked() and (self.dlg.comboBox_cha_time.currentText() == "Annual"):
        #     post_i_cha.sd_plot_annual(self) 
        # # Monthly output format given
        # elif self.dlg.radioButton_month.isChecked() and (self.dlg.comboBox_cha_time.currentText() == "Monthly"):
        #     post_i_cha.sd_plot_daily(self)
        # elif self.dlg.radioButton_month.isChecked() and (self.dlg.comboBox_cha_time.currentText() == "Annual"):
        #     post_i_cha.sd_plot_month_to_year(self)
        # # Annual output format given
        # elif self.dlg.radioButton_year.isChecked() and (self.dlg.comboBox_cha_time.currentText() == "Annual"):
        #     post_i_cha.sd_plot_daily(self)
        # else:
        #     msgBox = QMessageBox()
        #     msgBox.setText("There was a problem plotting the result!")
        #     msgBox.exec_()          

    def export_cha(self):
        if not self.dlg.groupBox_cha_obd.isChecked():
            post_i_cha.export_cha(self)
        if self.dlg.groupBox_cha_obd.isChecked():
            post_i_cha.export_cha_sims_obds(self)
    


    def plot_wt(self):
        if self.dlg.comboBox_hh_time.currentText() == "Daily":
            post_ii_wt.wt_plot_daily(self)
        elif self.dlg.comboBox_hh_time.currentText() == "Monthly":
            post_ii_wt.wt_plot_monthly(self)           
        elif self.dlg.comboBox_hh_time.currentText() == "Annual":
            post_ii_wt.wt_plot_annual(self)
        else:
            msgBox = QMessageBox()
            msgBox.setText("There was a problem plotting the result!")
            msgBox.exec_()  

    def export_wt(self):
        if self.dlg.comboBox_hh_time.currentText() == "Daily":
            post_ii_wt.export_wt_daily(self)
        elif self.dlg.comboBox_hh_time.currentText() == "Monthly":
            post_ii_wt.export_wt_monthly(self)         
        elif self.dlg.comboBox_hh_time.currentText() == "Annual":
            post_ii_wt.export_wt_annual(self)
        else:
            msgBox = QMessageBox()
            msgBox.setText("There was a problem plotting the result!")
            msgBox.exec_()  

    def plot_gwsw(self):
        post_iv_gwsw.plot_gwsw(self)

    def create_gwsw_shp(self):
        if self.dlg.checkBox_export_gwsw_shp.isChecked():
            post_iv_gwsw.create_gwsw_shp(self)
            self.dlg.pushButton_export_gwsw.setEnabled(True)
        else:
            self.dlg.pushButton_export_gwsw.setEnabled(False)

    def export_gwswToShp(self):
        post_iv_gwsw.export_gwswToShp(self)

    def export_gwsw(self):
        post_iv_gwsw.export_gwsw(self)

    def plot_std(self):
        # Daily
        if self.dlg.radioButton_day.isChecked() and self.dlg.radioButton_std_day.isChecked():
            post_v_wb.plot_wb_day(self)
        # Monthly Average
        elif self.dlg.radioButton_day.isChecked() and self.dlg.radioButton_std_month.isChecked():
            post_v_wb.plot_wb_dToM_A(self)
        # Annual Average
        elif self.dlg.radioButton_day.isChecked() and self.dlg.radioButton_std_year.isChecked():
            post_v_wb.plot_wb_dToM_A(self)
        # Monthly Total
        elif self.dlg.radioButton_month.isChecked() and self.dlg.radioButton_std_month.isChecked():
            post_v_wb.plot_wb_m_mToA(self)
        # Annual Average Monthly Total
        elif self.dlg.radioButton_month.isChecked() and self.dlg.radioButton_std_year.isChecked():
            post_v_wb.plot_wb_m_mToA(self)
        # Annual Total
        elif self.dlg.radioButton_year.isChecked() and self.dlg.radioButton_std_year.isChecked():
            post_v_wb.plot_wb_year(self)

    def export_wb(self):
        # Daily
        if self.dlg.radioButton_day.isChecked() and self.dlg.radioButton_std_day.isChecked():
            post_v_wb.export_wb_d(self)
        # Monthly Average
        elif self.dlg.radioButton_day.isChecked() and self.dlg.radioButton_std_month.isChecked():
            post_v_wb.export_wb_d(self)
        # Annual Average
        elif self.dlg.radioButton_day.isChecked() and self.dlg.radioButton_std_year.isChecked():
            post_v_wb.export_wb_d(self)
        # Monthly total
        elif self.dlg.radioButton_month.isChecked() and self.dlg.radioButton_std_month.isChecked():
            post_v_wb.export_wb_m(self)
        # Annual Average Monthly Total
        elif self.dlg.radioButton_month.isChecked() and self.dlg.radioButton_std_year.isChecked():
            post_v_wb.export_wb_m(self)
        # Annual Total
        elif self.dlg.radioButton_year.isChecked() and self.dlg.radioButton_std_year.isChecked():
            post_v_wb.export_wb_a(self)

    # Call QGIS actions to create and name a new project.
    def newProject(self):
        self.iface.actionNewProject().trigger()
        # save the project to force user to supply a name and location
        self.iface.actionSaveProjectAs().trigger()

        # allow time for project to be created
        time.sleep(1)
        proj = QgsProject.instance()

        if proj.fileName() == '':
            msgBox = QMessageBox()
            msgBox.setText("No project was created")
            msgBox.exec_()
            self.dlg.raise_()
            # return
        else:
            self.dlg.lineEdit_Project_Name.setText(QFileInfo(proj.fileName()).baseName())
            self.copyProjectfolder()

            #self.LoadExampleModelDir()
            self.dlg.raise_()
            time.sleep(1)
            # self.DB_CreateConnection()

            #global db
            db_functions.DB_CreateConnection(self)
            self.DB_Update_Project()

            smProjPath = proj.readPath("./")
            self.dlg.lineEdit_proj_path.setText(smProjPath)
            self.dlg.tabWidget.setTabEnabled(1, True)

            # create groups for layers
            root = QgsProject.instance().layerTreeRoot()
            apex_group = root.insertGroup(0, "APEX")
            mf_group = root.insertGroup(0, "MODFLOW")
            apexmf_group = root.insertGroup(0, "APEX-MODFLOW")
            self.dirs_and_paths()
            self.mfOptionOn() # enable


    def copyProjectfolder(self):
        # Location of the plugin which depend on user name
        plugindir = self.plugin_dir
        # Definition of the projectfolder for copy
        In_folder = os.path.normpath(plugindir + "/FOLDER_FOR_COPY")
        # name of the QGIS project stored in a QlineEdit
        Project_Name = self.dlg.lineEdit_Project_Name.text()
        # defintion of the out folder - i.e. projectfolder
        Out_folder_temp = QgsProject.instance().readPath("./")
        Out_folder = os.path.normpath(Out_folder_temp + "/" + Project_Name )

        # write path of projectfolder to interface
        # self.dlg.Project_Directory.setText(Out_folder)
        # copy the initial projectfolder
        if os.path.exists(Out_folder):
            distutils.dir_util.remove_tree(Out_folder)
        
        distutils.dir_util.copy_tree(In_folder, Out_folder)
        time.sleep(1)
        #the project database is updated
        #self.DB_CreateConnection()
        #self.DB_Update_Project()

    def dirs_and_paths(self):
        global APEXMOD_path_dict
        # project places
        Projectfolder = QgsProject.instance().readPath("./") 
        proj = QgsProject.instance() 
        Project_Name = QFileInfo(proj.fileName()).baseName()

        # definition of folders
        org_shps = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "GIS/org_shps")
        apexmf_shps = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "GIS/apexmf_shps")
        apexmf_model = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "APEX-MODFLOW")
        Table = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "GIS/Table")
        apexmf_exes = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "apexmf_exes")
        exported_files = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "exported_files")
        scn_folder = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "Scenarios")
        mf_model = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "APEX-MODFLOW/MODFLOW")
        salt_folder = os.path.normpath(Projectfolder + "/" + Project_Name + "/" + "APEX-MODFLOW/SALINITY")

        APEXMOD_path_dict = {
                                'org_shps': org_shps,
                                'apexmf_shps': apexmf_shps,
                                'apexmf_model': apexmf_model,
                                'Table': Table,
                                'apexmf_exes': apexmf_exes,
                                'exported_files': exported_files,
                                'Scenarios': scn_folder,
                                'MODFLOW': mf_model,
                                'SALINITY': salt_folder
                                }
        return APEXMOD_path_dict

    def load_apex_model(self):
        load_inputs.select_apex_model(self)

    def load_sub(self):
        load_inputs.sub_shapefile(self)
        self.mfOptionOn() # enable
    
    def load_riv(self):
        load_inputs.riv_shapefile(self)
        self.mfOptionOn() # enable

    def load_mf_model(self):
        load_inputs.select_mf_model(self)

    #----------------------------------------------------------------------------#
    #-----------------------databae features-------------------------------------#
    #----------------------------------------------------------------------------#
    """ Functions relating connection, update, deletes and other changes of the 
    SQLite database""" 
                    
    # def DB_CreateConnection(self):
    #   global db
    #   db = QtSql.QSqlDatabase.addDatabase('QSQLITE')
    #   proj = QgsProject.instance()
    #   db_path = QgsProject.instance().readPath("./")
    #   db_folder = QFileInfo(proj.fileName()).baseName()
        
           
    #   db_subfolder = os.path.normpath(db_path + "/" + db_folder +  "/DB")
    #   db_file = os.path.join(db_subfolder, "DB_SM.db")
    #   db.setDatabaseName(db_file)
    #   # self.dlg.DB_Project_Database.setText(db_file)
        
    #   db.setHostName("localhost")
    #   db.setPort(5432)

    #   #db.setUserName("root")
    #   db.open()
    #   if db.open():
    #       msgBox = QMessageBox()
    #       msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
    #       msgBox.setWindowTitle("Ready!")
    #       msgBox.setText("Connected to Database")
    #       msgBox.exec_()
    #       self.dlg.raise_() # Pop the dialog after execution
            
    #       query = QtSql.QSqlQuery(db)
    #       #Th Keep track of the references in the scenarios the foreign key statement is activated:
    #       #https://pythonschool.net/databases/referential-integrity/
    #       query.exec_("PRAGMA foreign_keys = ON")

    #   else:
    #       QMessageBox.critical(None, "Database Error",
    #           db.lastError().text()) 
    #       return False


    def DB_Update_Project(self):
        db = db_functions.db_variable(self)
        query = QtSql.QSqlQuery(db)
        query.prepare("UPDATE project SET DB_project_name=:UP1 WHERE ID=1 ")
        query.bindValue ( ":UP1", self.dlg.lineEdit_Project_Name.text())
        query.exec_()    


    def DB_Pull_Project(self):
        db = db_functions.db_variable(self)      
        query = QtSql.QSqlQuery(db)
        query.exec_("SELECT DB_project_name FROM project WHERE ID = 1 ")
        LK = str(query.first())
        self.dlg.lineEdit_Project_Name.setText(query.value(0))

        #self.dlg.Project_Directory.setText(query.value(1))
        #self.dlg.CRS.setText(query.value(2))

    # def DB_Pull_mf_inputs(self):      
    #   query = QtSql.QSqlQuery(db)
    #   query.exec_("SELECT user_val FROM mf_inputs WHERE parNames = 'ss' ")
    #   LK = str(query.first())
    #   self.lineEdit_ss.setText(query.value(0))
    #   #self.dlg.Project_Directory.setText(query.value(1))
    #   #self.dlg.CRS.setText(query.value(2))


    def checkMF(self):
        modflow_functions.create_modflow_mfn(self)
        modflow_functions.modify_modflow_oc(self)
        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setWindowTitle("Completed!")
        msgBox.setText("Checking MODFLOW inputs has been completed!")
        msgBox.exec_()

    # == some day
    # def swat_analyze_subbasin(self):
    #     output_rch = os.path.join(APEXMOD_path_dict['apexmf_model'], "output.rch")
    #     #read the output.rch
    #     with open(output_rch, "r") as f:
    #         for line in f:
    #             if line.strip().startswith("RCH"):
    #                 reach_subbasins = [line.strip().split() for line in f]

    #     included_cols = [1]
    #     subbasins = [[each_list[i] for i in included_cols] for each_list in reach_subbasins]
    #     subbasin_list = []
    #     for sub in subbasins:
    #         if sub not in subbasin_list:
    #             subbasin_list.append(sub)

    #     subbasin_list_1 = []
    #     for sub in subbasin_list:
    #         subbasin_list_1.extend(sub)

    def createMF(self):
        self.dlg.progressBar_sm_link.setValue(0)
        modflow_functions.MF_grid(self)
        self.dlg.progressBar_sm_link.setValue(20)
        QCoreApplication.processEvents()
        
        modflow_functions.create_grid_id(self)
        self.dlg.progressBar_sm_link.setValue(60)
        QCoreApplication.processEvents()

        modflow_functions.create_row(self)
        self.dlg.progressBar_sm_link.setValue(70)
        QCoreApplication.processEvents()
        
        modflow_functions.create_col(self)
        self.dlg.progressBar_sm_link.setValue(80)
        QCoreApplication.processEvents()
        
        modflow_functions.create_elev_mf(self)
        self.dlg.progressBar_sm_link.setValue(100)
        QCoreApplication.processEvents()
        

        ### Use the "use_sub_shapefile" function from CreateMFmodel_dialog --> not working
        ### reason not working is no "self.checkBox_use_sub.isChecked():"
        # class_mf = createMFmodelDialog(self) # make the class the object
        # class_mf.use_sub_shapefile()
        # time = datetime.now().strftime('[%m/%d/%y %H:%M:%S]')

        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setWindowTitle("Created!")
        msgBox.setText("'mf_grid' shapefile was created!")
        msgBox.exec_()

    def geoprocessing_prepared(self):
        from datetime import datetime
        self.dlg.checkBox_filesPrepared.setChecked(0)
        self.dlg.progressBar_sm_link.setValue(0)
        self.dlg.textEdit_sm_link_log.append('+ '*15 +'  Start Linking Process  '+' +'*15)

        # Calculate SUB area
        linking_process.calculate_sub_area(self)
        self.dlg.progressBar_sm_link.setValue(20)         
        QCoreApplication.processEvents()

        # Create sub_grid
        linking_process.sub_grid(self)
        self.dlg.progressBar_sm_link.setValue(40)
        QCoreApplication.processEvents()

        
        linking_process.create_sub_grid_filter(self)  # for invalid geometry 
        linking_process.delete_sub_grid_with_zero(self)  # for invalid geometry
        self.dlg.progressBar_sm_link.setValue(80)
        QCoreApplication.processEvents()

        ### below function can be used for unstructered grid
        # modflow_functions.calculate_grid_area(self)  # can be used for unstructered grid
        # self.dlg.progressBar_sm_link.setValue(80)
        # self.dlg.textEdit_sm_link_log.append('MODFLOW grid area is calculated!')
        # QCoreApplication.processEvents()

        # ---------------------------------------------------------------
        # '''
        # Export tables from layers
        time = datetime.now().strftime('[%m/%d/%y %H:%M:%S]')
        self.dlg.textEdit_sm_link_log.append(time+' -> ' + 'Exporting tables from layers ... processing') 
        self.dlg.progressBar_sm_link.setValue(96)     
        linking_process.export_sub_grid(self)
        linking_process.export_grid_sub(self)
        linking_process.copylinkagefiles(self)
        self.dlg.progressBar_sm_link.setValue(100)
        time = datetime.now().strftime('[%m/%d/%y %H:%M:%S]')
        self.dlg.textEdit_sm_link_log.append(time+' -> ' + 'Exporting tables from layers ... passed')    
        QCoreApplication.processEvents()
        self.dlg.checkBox_filesPrepared.setChecked(1)
        
        msgBox = QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        msgBox.setWindowTitle("Completed!")
        msgBox.setText("Linking process has been completed successfully!")
        msgBox.exec_()
        '''
        questionBox = QMessageBox()
        questionBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
        reply = QMessageBox.question(
                            questionBox, 'Create?',
                            'Do you wish to create the linkage files?', QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            linking_process.run_CreateSWATMF(self)
            linking_process.copylinkagefiles(self)
            msgBox.setWindowTitle("Exported!")
            msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
            msgBox.setText("Linkage files have been exported to your APEX-MODFLOW folder!")
            msgBox.exec_()
            self.dlg.tabWidget.setTabEnabled(2, True)
        '''
        self.dlg.tabWidget.setTabEnabled(2, True)
        self.define_sim_period()            


    def run_apexmf_model(self):
        import subprocess
        output_dir = APEXMOD_path_dict['apexmf_model']
        bnam_latest = "amrs_rel24-002.exe"
        bnam_default = "apexmf1.1_64rel.exe"
        if os.path.isfile(os.path.join(output_dir, bnam_latest)):
            exe_file = os.path.normpath(os.path.join(output_dir, bnam_latest))
        else:
            exe_file = os.path.normpath(os.path.join(output_dir, bnam_default))

        # os.startfile(File_Physical)
        p = subprocess.Popen(exe_file , cwd = output_dir) # cwd -> current working directory    
        # p.wait()  ## following line to wait till running is finished. 

    def check_outputs(self):
        self.dirs_and_paths()
        output_dir = APEXMOD_path_dict['MODFLOW']
        output_files = ["amf_MF_recharge.out", "amf_apex_channel.out"]
        if all(os.path.isfile(os.path.join(output_dir, x)) for x in output_files):
            post_i_cha.read_sub_no(self)
            post_i_cha.read_cha_vars(self)
            self.dlg.tabWidget.setTabEnabled(3, True)
        else:
            self.dlg.tabWidget.setTabEnabled(3, False)

    def check_outputs_rt3d(self):
        self.dirs_and_paths()
        output_dir = APEXMOD_path_dict['MODFLOW']
        output_files = ["apexmf_link.txt", "amf_RT3D_cNO3_monthly.out"]
        if all(os.path.isfile(os.path.join(output_dir, x)) for x in output_files):
            self.dlg.tabWidget.setTabEnabled(4, True)
            post_ix_solute_hyd.read_sub_no(self)
            post_ix_solute_hyd.get_compNames(self)
        else:
            self.dlg.tabWidget.setTabEnabled(4, False)


    # figured it out by trials and errors -------------------------------
    # def loadDEM_main(self):
    #   class_mf = createMFmodelDialog(self) # make the class the object
    #   # class_mf.loadDEM() # Does it make run?
    #   DEM =  class_mf.loadDEM()
    #   self.dlg.lineEdit_DEM_main.setText(DEM)
    #   self.mfOptionOn()
    # # Then how could i fill up the rest part? > I did it, whooray!!! ----------------------------

    def use_sub_shapefile(self):
        from qgis.PyQt import QtCore, QtGui, QtSql
        try:
            input1 = QgsProject.instance().mapLayersByName("sub (APEX)")[0]
            #provider = layer.dataProvider()
            if self.dlg.checkBox_default_extent.isChecked():
                name = "mf_boundary"
                name_ext = "mf_boundary.shp"
                output_dir = APEXMOD_path_dict['org_shps']
                # output_file = os.path.normpath(os.path.join(output_dir, name))

                mf_boundary = os.path.join(output_dir, name_ext)
                processing.run("qgis:dissolve", input1, True, None, mf_boundary)

                # defining the outputfile to be loaded into the canvas
                layer = QgsVectorLayer(mf_boundary, '{0} ({1})'.format("mf_boundary","MODFLOW"), 'ogr')

                # Put in the group
                root = QgsProject.instance().layerTreeRoot()
                mf_group = root.findGroup("MODFLOW")    
                QgsProject.instance().addMapLayer(layer, False)
                mf_group.insertChildNode(0, QgsLayerTreeLayer(layer))
                #subpath = layer.source()
        except:
            msgBox = QMessageBox()
            msgBox.setWindowIcon(QtGui.QIcon(':/APEXMOD/pics/am_icon.png'))
            msgBox.setWindowTitle("Oops!")
            msgBox.setText("Please, use the extent of Subbasin area!")
            msgBox.exec_()

    def cvtElevToR(self):
        # nrow, ncol, delr, delc = modflow_functions.MF_grid(self) # --> this is problem

        extlayer = QgsProject.instance().mapLayersByName("mf_grid (MODFLOW)")[0]
        input1 = QgsProject.instance().mapLayersByName("mf_act_grid (MODFLOW)")[0]

        # Find .dis file and read number of rows, cols, x spacing, and y spacing (not allowed to change)
        for filename in glob.glob(str(APEXMOD_path_dict['apexmf_model'])+"/*.dis"):
            with open(filename, "r") as f:
                data = []
                for line in f.readlines():
                    if not line.startswith("#"):
                        data.append(line.replace('\n', '').split())
            nrow = int(data[0][1])
            ncol = int(data[0][2])
            delr = float(data[2][1]) # is the cell width along rows (y spacing)
            delc = float(data[3][1]) # is the cell width along columns (x spacing).
        # get extent
        ext = extlayer.extent()
        xmin = ext.xMinimum()
        xmax = ext.xMaximum()
        ymin = ext.yMinimum()
        ymax = ext.yMaximum()
        extent = "{a},{b},{c},{d}".format(a = xmin, b = xmax, c = ymin, d = ymax)
        name = 'top_elev'
        name_ext = "top_elev.tif"
        output_dir = APEXMOD_path_dict['org_shps']
        output_raster = os.path.join(output_dir, name_ext)
        processing.run(
            "gdalogr:rasterize",
            input1,
            "elev_mean", 1, delc, delr,
            extent,
            False, 5, "-9999", 0, 75, 6, 1, False, 0, "",
            output_raster)

        # fileInfo = QFileInfo(output_raster)
        # path = fileInfo.filePath()
        # baseName = fileInfo.baseName()

        # for raster no 'ogr'
        layer = QgsRasterLayer(output_raster, '{0} ({1})'.format("top_elev","MODFLOW"))
        
        # Put in the group
        root = QgsProject.instance().layerTreeRoot()
        mf_group = root.findGroup("MODFLOW")    
        QgsProject.instance().addMapLayer(layer, False)
        mf_group.insertChildNode(0, QgsLayerTreeLayer(layer))

    # put another ui in main ui
    def showCreateMFmodel_dialog(self):
        self.dlgMF = createMFmodel_dialog.createMFmodelDialog(self.iface)
        self.dlgMF.show()
        self.dlgMF.exec_()

    # thres_dhru
    def thres_dhru(self):
        if self.dlg.groupBox_threshold.isChecked():
            self.dlg.horizontalSlider_ol_area.setEnabled(True)
            self.dlg.label_dhru_size.setEnabled(True)
            dhru_max_size = modflow_functions.check_grid_size(self)
            self.dlg.horizontalSlider_ol_area.setMaximum(900)
            self.dlg.horizontalSlider_ol_area.setMaximum(dhru_max_size)
            self.dlg.horizontalSlider_ol_area.setSingleStep(900)
            self.dlg.horizontalSlider_ol_area.setValue(900)
            self.dlg.horizontalSlider_ol_area.setPageStep(900)
        else:
            self.dlg.horizontalSlider_ol_area.setEnabled(False)
            self.dlg.label_dhru_size.setEnabled(False)            

    def thres_dhru_value(self):
        dhru_size = self.dlg.horizontalSlider_ol_area.value()
        self.dlg.label_dhru_size.setText(str(dhru_size))

    # show help dialog
    def showHelp_dialog(self):
        self.dlghelp = help_dialog.showhelpdialog(self.iface)
        self.dlghelp.show()

        self.dlghelp.exec_()

    def test_table(self):
        # db_functions.db_variable(self)
        model = QtSql.QSqlTableModel()
        model.setEditStrategy(QtSql.QSqlTableModel.OnFieldChange)
        model.setTable("mf_inputs")
        #SQL_temp = str("parNames = ss")
        #model.setFilter(SQL_temp)
        model.select()
        model.setHeaderData(1, QtCore.Qt.Horizontal, "what")
        self.dlg.tableView_test.setModel(model)


    # NOTE: Tab5 --- RT related functions tab5
    # Let's combine rt3d / salt here
    def solute_year_label(self):
        current_year = self.dlg.horizontalSlider_solute_start_year.value()
        self.dlg.label_solute_year.setText(str(current_year))

    def solute_plot(self):
        post_ix_solute_hyd.solute_plot(self)

    def export_solute_df(self):
        post_ix_solute_hyd.export_solute_df(self)

    def import_rt3d_salt_dates(self):
        if (
            self.dlg.groupBox_export_solutes.isChecked() and
            self.dlg.comboBox_solutes.currentText() != ""
            ):
            comp = self.dlg.comboBox_solutes.currentText().replace('(', '').replace(')', '').strip().split()[1].lower()
            if (
                comp != "solute" and
                self.dlg.radioButton_rt3d_m.isChecked() and
                comp != "nitrate" and
                comp != "phosphorus"
                ):
                post_viii_salt.read_salt_dates(self)
            if (
                (comp == "nitrate" or comp == "phosphorus") and
                self.dlg.radioButton_rt3d_m.isChecked()
                ):
                post_vii_nitrate.read_rt3d_dates(self)
                post_vii_nitrate.read_mf_nOflayers(self)

    def create_rt3d_salt_shps(self):
        if (
            self.dlg.groupBox_export_solutes.isChecked() and
            self.dlg.comboBox_solutes.currentText() != ""
            ):
            comp = self.dlg.comboBox_solutes.currentText().replace('(', '').replace(')', '').strip().split()[1].lower()
            if (
                comp != "solute" and
                self.dlg.radioButton_rt3d_m.isChecked() and
                self.dlg.radioButton_conc.isChecked() and
                comp != "nitrate" and
                comp != "phosphorus"
                ):
                post_viii_salt.create_salt_grid_shps(self) 
            if (
                comp != "solute" and
                self.dlg.radioButton_rt3d_m.isChecked() and
                self.dlg.radioButton_conc.isChecked() and
                comp == "nitrate" or
                comp == "phosphorus"
                ):
                post_vii_nitrate.create_rt3d_shps(self)
            if (
                comp != "solute" and
                # self.dlg.radioButton_rt3d_m.isChecked() and
                self.dlg.radioButton_perc.isChecked() and
                comp == "nitrate" or
                comp == "phosphorus"
                ):
                post_vii_nitrate.create_rt3d_perc_shps(self)
                post_vii_nitrate.read_perc_dates(self)

    def get_compNames(self):
        post_vii_nitrate.get_compNames(self)

    def create_avg_m_shps(self):
        comp = self.dlg.comboBox_solutes.currentText().replace('(', '').replace(')', '').strip().split()[1].lower()
        if (
            (comp == 'nitrate' or
            comp == 'phosphorus') and
            self.dlg.mGroupBox_rt_avg.isChecked()):
            post_vii_nitrate.create_rt_avg_mon_shp(self)
        if (
            (comp == 'sulfate' or
            comp == 'calcium' or
            comp == 'magnesium' or
            comp == 'sodium' or
            comp == 'potassium' or
            comp == 'chloride' or
            comp == 'carbonate' or
            comp == 'bicarbonate') and
            (self.dlg.mGroupBox_rt_avg.isChecked())
            ):
            post_viii_salt.create_salt_avg_mon_shp(self)
    
    def export_rt_cno3_avg_m(self):
        post_vii_nitrate.get_rt_cno3_avg_m_df(self)
        post_vii_nitrate.export_rt_cno3_avg_m(self)

    def read_vector_maps(self):
        post_vii_nitrate.read_vector_maps(self)

    def cvt_vtr(self):
        post_vii_nitrate.cvt_vtr(self)
    
    def create_salt_grid_shapefile(self):
        if self.dlg.radioButton_rt3d_m.isChecked():
            post_viii_salt.read_salt_dates(self)
            post_viii_salt.create_salt_grid_shapefile(self)

    def export_solute_results(self):
        comp = self.dlg.comboBox_solutes.currentText().replace('(', '').replace(')', '').strip().split()[1].lower()
        if (
            (comp == 'nitrate' or
            comp == 'phosphorus') and
            self.dlg.radioButton_conc.isChecked() and
            not self.dlg.mGroupBox_rt_avg.isChecked()
            ):
            post_vii_nitrate.export_rt_cno3(self)
        if (
            (comp == 'nitrate' or
            comp == 'phosphorus') and
            self.dlg.radioButton_conc.isChecked() and
            self.dlg.mGroupBox_rt_avg.isChecked()
            ):
            post_vii_nitrate.get_rt_cno3_avg_m_df(self)
            post_vii_nitrate.export_rt_cno3_avg_m(self)

        if (
            (comp == 'nitrate' or
            comp == 'phosphorus') and
            self.dlg.radioButton_perc.isChecked() and
            not self.dlg.mGroupBox_rt_avg.isChecked()
            ):
            post_vii_nitrate.export_perc_no3(self)
        # if (
        #     (comp == 'nitrate' or
        #     comp == 'phosphorus') and
        #     self.dlg.radioButton_conc.isChecked() and
        #     self.dlg.mGroupBox_rt_avg.isChecked()
        #     ):
        #     post_vii_nitrate.get_rt_cno3_avg_m_df(self)
        #     post_vii_nitrate.export_rt_cno3_avg_m(self)
        if (
            (comp == 'sulfate' or
            comp == 'calcium' or
            comp == 'magnesium' or
            comp == 'sodium' or
            comp == 'potassium' or
            comp == 'chloride' or
            comp == 'carbonate' or
            comp == 'bicarbonate') and
            not self.dlg.mGroupBox_rt_avg.isChecked()
            ):
            post_viii_salt.salt_export_result(self)
        if (
            (comp == 'sulfate' or
            comp == 'calcium' or
            comp == 'magnesium' or
            comp == 'sodium' or
            comp == 'potassium' or
            comp == 'chloride' or
            comp == 'carbonate' or
            comp == 'bicarbonate') and
            (self.dlg.mGroupBox_rt_avg.isChecked())
            ):
            post_viii_salt.get_salt_avg_m_df(self)
            post_viii_salt.export_salt_avg_m(self)
        # elif (
        #         self.dlg.comboBox_solutes.currentText() == 'NO3 (Nitrate)' and 
        #         self.dlg.mGroupBox_rt_avg.isChecked()):
        #     self.export_rt_cno3_avg_m()

    # NOTE: 5th | salt ion in channel
    def salt_year_label(self):
        current_year = self.dlg.horizontalSlider_salt_start_year.value()
        self.dlg.label_salt_year.setText(str(current_year))

    def activate_salt_channel(self):
        if self.dlg.groupBox_salt_channel.isChecked():
            self.salt_ions_df = post_ix_solute_hyd.read_salt_ions_channel(self)

    def salt_ions_plot(self):
        # post_ix_solute_hyd.read_salt_ions_channel(self)
        salt_ions_df = self.salt_ions_df
        if (
            not self.dlg.checkBox_salt_stacked.isChecked() and 
            not self.dlg.groupBox_salt_obd.isChecked()):
            post_ix_solute_hyd.salt_plot(self, salt_ions_df)
        if (
            self.dlg.checkBox_salt_stacked.isChecked()
            ):
            post_ix_solute_hyd.salt_stacked_plot(self, salt_ions_df)
        if (
            not self.dlg.checkBox_salt_stacked.isChecked() and
            self.dlg.groupBox_salt_obd.isChecked()
            ):
            post_ix_solute_hyd.salt_sim_obd_plot(self, salt_ions_df)
    
    def salt_export(self):
        salt_ions_df = self.salt_ions_df
        if (
            not self.dlg.checkBox_salt_stacked.isChecked() and 
            not self.dlg.groupBox_salt_obd.isChecked()):
            post_ix_solute_hyd.export_salt_ion(self, salt_ions_df)
        if self.dlg.checkBox_salt_stacked.isChecked():
            post_ix_solute_hyd.export_salt_mass_conc(self, salt_ions_df)
        if (
            not self.dlg.checkBox_salt_stacked.isChecked() and
            self.dlg.groupBox_salt_obd.isChecked()
            ):
            post_ix_solute_hyd.export_salt_sims_obds(self, salt_ions_df)
    
    def activate_salt_obd(self):
        if self.dlg.groupBox_salt_obd.isChecked():
            post_ix_solute_hyd.read_salt_obd_files(self)

    def get_salt_obd_gages(self):
        post_ix_solute_hyd.get_salt_obd_gages(self)

    def activate_cha_obd(self):
        if self.dlg.groupBox_cha_obd.isChecked():
            post_i_cha.read_cha_obd_files(self)

    def get_cha_obd_gages(self):
        post_i_cha.get_cha_obd_gages(self)

# ---

    # put another ui in main ui
    def openRT3Dui(self):
        linking_process.create_rt3d_grid(self)
        self.rt3d = create_rt3d_dlg.CreateRT3D(self.iface)
        self.rt3d.show()
        self.rt3d.exec_()

    # put another ui in main ui
    def open_salt_ui(self):
        self.salt = create_salt_dlg.CreateSALT(self.iface)
        self.salt.show()
        self.salt.exec_()