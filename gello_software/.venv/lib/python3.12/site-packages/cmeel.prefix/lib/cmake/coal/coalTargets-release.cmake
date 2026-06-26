#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "coal::coal" for configuration "Release"
set_property(TARGET coal::coal APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(coal::coal PROPERTIES
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "assimp::assimp;Qhull::qhull_r"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libcoal.so.3.0.1"
  IMPORTED_SONAME_RELEASE "libcoal.so.3.0.1"
  )

list(APPEND _cmake_import_check_targets coal::coal )
list(APPEND _cmake_import_check_files_for_coal::coal "${_IMPORT_PREFIX}/lib/libcoal.so.3.0.1" )

# Import target "coal::coal_pywrap" for configuration "Release"
set_property(TARGET coal::coal_pywrap APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(coal::coal_pywrap PROPERTIES
  IMPORTED_COMMON_LANGUAGE_RUNTIME_RELEASE ""
  IMPORTED_LOCATION_RELEASE "${PACKAGE_PREFIX_DIR}/lib/python3.12/site-packages/coal/coal_pywrap.cpython-312-x86_64-linux-gnu.so"
  IMPORTED_NO_SONAME_RELEASE "TRUE"
  )

list(APPEND _cmake_import_check_targets coal::coal_pywrap )
list(APPEND _cmake_import_check_files_for_coal::coal_pywrap "${PACKAGE_PREFIX_DIR}/lib/python3.12/site-packages/coal/coal_pywrap.cpython-312-x86_64-linux-gnu.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
