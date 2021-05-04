import qt, ctk, slicer
from . import pqWidget

class VisualizationWidget(pqWidget):
  """
  A "QWidget"-like class that manages some of the viewer options
  used during registration
  """

  def __init__(self,logic):
    super().__init__()
    self.rockCount = 0
    self.rocking = False
    self.rockTimer = None
    self.flickerTimer = None
    self.logic = logic
    self.revealCursor = None
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
    checkBox = qt.QCheckBox()
    checkBox.text = "RevealCursor"
    checkBox.checked = False
    checkBox.connect('toggled(bool)', self.revealToggled)
    layout.addWidget(checkBox)
    self.groupBoxLayout.addRow("Display", checkboxHolder)

    #
    # fade slider
    #
    fadeHolder = qt.QWidget()
    fadeLayout = qt.QHBoxLayout()
    fadeHolder.setLayout(fadeLayout)
    self.fadeSlider = ctk.ctkSliderWidget()
    self.fadeSlider.minimum = 0
    self.fadeSlider.maximum = 1.0
    self.fadeSlider.value = 0.5
    self.fadeSlider.singleStep = 0.05
    self.fadeSlider.connect('valueChanged(double)', self.onFadeChanged)
    fadeLayout.addWidget(self.fadeSlider)

    #
    # Rock and Flicker
    #
    animaHolder = qt.QWidget()
    animaLayout = qt.QVBoxLayout()
    animaHolder.setLayout(animaLayout)
    fadeLayout.addWidget(animaHolder)
    # Rock
    checkBox = qt.QCheckBox()
    checkBox.text = "Rock"
    checkBox.checked = False
    checkBox.connect('toggled(bool)', self.onRockToggled)
    animaLayout.addWidget(checkBox)
    # Flicker
    checkBox = qt.QCheckBox()
    checkBox.text = "Flicker"
    checkBox.checked = False
    checkBox.connect('toggled(bool)', self.onFlickerToggled)
    animaLayout.addWidget(checkBox)

    self.groupBoxLayout.addRow("Fade", fadeHolder)

    #
    # zoom control
    #
    zoomHolder = qt.QWidget()
    layout = qt.QHBoxLayout()
    zoomHolder.setLayout(layout)
    zooms = {"+": 0.7, "-": 1.3, "Fit": "Fit",}
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

  def revealToggled(self,checked):
    """Turn the RevealCursor on or off
    """
    if self.revealCursor:
      self.revealCursor.tearDown()
    if checked:
      import CompareVolumes
      self.revealCursor = CompareVolumes.LayerReveal()

  def onFadeChanged(self,value):
    """Update all the slice compositing"""
    nodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
    for node in nodes.values():
      node.SetForegroundOpacity(value)

  def rock(self):
    if not self.rocking:
      self.rockTimer = None
      self.fadeSlider.value = 0.5
    if self.rocking:
      if not self.rockTimer:
        self.rockTimer = qt.QTimer()
        self.rockTimer.start(50)
        self.rockTimer.connect('timeout()', self.rock)
      import math
      self.fadeSlider.value = 0.5 + math.sin(self.rockCount / 10. ) / 2.
      self.rockCount += 1

  def onRockToggled(self,checked):
    self.rocking = checked
    self.rock()

  def flicker(self):
    if not self.flickering:
      self.flickerTimer = None
      self.fadeSlider.value = 0.5
    if self.flickering:
      if not self.flickerTimer:
        if self.fadeSlider.value == 0.5:
          self.fadeSlider.value = 0.25
        self.flickerTimer = qt.QTimer()
        self.flickerTimer.start(300)
        self.flickerTimer.connect('timeout()', self.flicker)
      import math
      self.fadeSlider.value = 1.0 - self.fadeSlider.value

  def onFlickerToggled(self,checked):
    self.flickering = checked
    self.flicker()

  def onZoom(self,zoomFactor):
    import CompareVolumes
    compareLogic = CompareVolumes.CompareVolumesLogic()
    compareLogic.zoom(zoomFactor)


