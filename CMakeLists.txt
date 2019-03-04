cmake_minimum_required(VERSION 3.13.0)

#-----------------------------------------------------------------------------
set(MODULE_NAME LandmarkRegistration)
set(LIB_NAME RegistrationLib)

#-----------------------------------------------------------------------------
if(NOT Slicer_SOURCE_DIR)
  find_package(Slicer REQUIRED)
  include(${Slicer_USE_FILE})
endif()

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ${LIB_NAME}/__init__.py
  ${LIB_NAME}/AffinePlugin.py
  ${LIB_NAME}/Landmarks.py
  ${LIB_NAME}/LocalBRAINSFitPlugin.py
  ${LIB_NAME}/LocalSimpleITKPlugin.py
  ${LIB_NAME}/RegistrationPlugin.py
  ${LIB_NAME}/RegistrationState.py
  ${LIB_NAME}/ThinPlatePlugin.py
  ${LIB_NAME}/Visualization.py
  ${LIB_NAME}/pqWidget.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/LandmarkRegistration.png
  Resources/Icons/icon_Add.png
  Resources/Icons/icon_Active.png
  Resources/Icons/icon_Trash.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT LandmarkRegistration.py)

endif()
