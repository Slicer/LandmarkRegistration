cmake_minimum_required(VERSION 2.8.7)

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
  ${LIB_NAME}Lib/__init__.py
  ${LIB_NAME}Lib/AffinePlugin.py
  ${LIB_NAME}Lib/RegistrationPlugin.py
  ${LIB_NAME}Lib/RegistrationState.py
  ${LIB_NAME}Lib/ThinPlatePlugin.py
  ${LIB_NAME}Lib/Visualization.py
  ${LIB_NAME}Lib/pqWidget.py
  )

set(MODULE_PYTHON_RESOURCES
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
