from __main__ import vtk, qt, ctk, slicer
import RegistrationLib

class VisualizationWidget(RegistrationLib.pqWidget):
  """
  A "QWidget"-like class that manages some of the viewer options
  used during registration
  """

  def __init__(self,logic):
    super(VisualizationWidget,self).__init__()
    self.logic = logic
    self.volumes = ("Fixed", "Moving", "Transformed",)
    self.layoutOptions = ("Axial", "Coronal", "Sagittal", "Axi/Sag/Cor",)
    self.layoutOption = 'Axi/Sag/Cor'
    self.volumeDisplayCheckboxes = {}

    # mimic the structure of the LandmarksWidget for visual
    # consistency (it needs sub widget so it can delete and refresh the internals)
    self.widget = qt.QWidget()
    self.layout = qt.QFormLayout(self.widget)
    self.boxHolder = qt.QWidget()
    self.boxHolder.setLayout(qt.QVBoxLayout())
    self.layout.addRow(self.boxHolder)
    self.groupBox = qt.QGroupBox("Visualization")
    self.groupBoxLayout = qt.QFormLayout(self.groupBox)
    self.boxHolder.layout().addWidget(self.groupBox)

    #
    # layout selection
    #
    layoutHolder = qt.QWidget()
    layout = qt.QHBoxLayout()
    layoutHolder.setLayout(layout)
    for layoutOption in self.layoutOptions:
      layoutButton = qt.QPushButton(layoutOption)
      layoutButton.connect('clicked()', lambda lo=layoutOption: self.selectLayout(lo))
      layout.addWidget(layoutButton)
    self.groupBoxLayout.addRow("Layout", layoutHolder)

    #
    # Volume display selection
    #
    checkboxHolder = qt.QWidget()
    layout = qt.QHBoxLayout()
    checkboxHolder.setLayout(layout)
    for volume in self.volumes:
      checkBox = qt.QCheckBox()
      checkBox.text = volume
      checkBox.checked = True
      checkBox.connect('toggled(bool)', self.updateVisualization)
      layout.addWidget(checkBox)
      self.volumeDisplayCheckboxes[volume] = checkBox
    self.groupBoxLayout.addRow("Display", checkboxHolder)

    #
    # fade slider
    #
    self.fadeSlider = ctk.ctkSliderWidget()
    self.fadeSlider.minimum = 0
    self.fadeSlider.maximum = 1.0
    self.fadeSlider.value = 0.5
    self.fadeSlider.singleStep = 0.05
    self.fadeSlider.connect('valueChanged(double)', self.onFadeChanged)
    self.groupBoxLayout.addRow("Cross Fade", self.fadeSlider)

    #
    # zoom control
    #
    zoomHolder = qt.QWidget()
    layout = qt.QHBoxLayout()
    zoomHolder.setLayout(layout)
    zooms = {"+": 0.9, "-": 1.1, "Fit": "Fit",}
    for zoomLabel,zoomFactor in zooms.items():
      zoomButton = qt.QPushButton(zoomLabel)
      zoomButton.connect('clicked()', lambda zf=zoomFactor: self.onZoom(zf))
      layout.addWidget(zoomButton)
    self.groupBoxLayout.addRow("Zoom", zoomHolder)

  def selectLayout(self,layoutOption):
    """Keep track of the currently selected layout and trigger an update"""
    self.layoutOption = layoutOption
    self.updateVisualization()

  def updateVisualization(self):
    """When there's a change in the layout requested by either
    the layout or the volume display options, emit a signal that
    summarizes their state"""
    volumesToShow = []
    for volume in self.volumes:
      if self.volumeDisplayCheckboxes[volume].checked:
        volumesToShow.append(volume)
    self.fadeSlider.enabled = "Transformed" in volumesToShow
    self.emit("layoutRequested(mode,volumesToShow)", (self.layoutOption,volumesToShow))

  def onFadeChanged(self,value):
    """Update all the slice compositing"""
    nodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
    for node in nodes.values():
      node.SetForegroundOpacity(value)

  def onZoom(self,zoomFactor):
    import CompareVolumes
    compareLogic = CompareVolumes.CompareVolumesLogic()
    compareLogic.zoom(zoomFactor)


