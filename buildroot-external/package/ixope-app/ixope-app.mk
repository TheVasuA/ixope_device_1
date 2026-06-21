################################################################################
#
# ixope-app — IXOPE Medical Device Application
#
################################################################################

IXOPE_APP_VERSION = 1.0
IXOPE_APP_SITE = $(BR2_EXTERNAL_IXOPE_PATH)/..
IXOPE_APP_SITE_METHOD = local
IXOPE_APP_SETUP_TYPE = none

IXOPE_APP_DEPENDENCIES = \
	python3 \
	python-pillow \
	python-numpy \
	python-flask \
	python-requests \
	opencv4 \
	xserver_xorg-server \
	xlib_libX11

define IXOPE_APP_INSTALL_TARGET_CMDS
	# Install the application code
	$(INSTALL) -d $(TARGET_DIR)/opt/ixope
	cp -a $(@D)/app.py $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/__init__.py $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/__main__.py $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/updater.py $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/VERSION $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/config $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/camera $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/hardware $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/network $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/storage $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/flask_server $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/ui $(TARGET_DIR)/opt/ixope/
	cp -a $(@D)/deploy/boot_logo.gif $(TARGET_DIR)/opt/ixope/ 2>/dev/null || true

	# Create writable data directory
	$(INSTALL) -d $(TARGET_DIR)/var/ixope-data
	$(INSTALL) -d $(TARGET_DIR)/var/ixope-data/logs
	$(INSTALL) -d $(TARGET_DIR)/var/ixope-data/captured_images
	$(INSTALL) -d $(TARGET_DIR)/var/ixope-data/recorded_videos

	# Install init script
	$(INSTALL) -D -m 0755 $(BR2_EXTERNAL_IXOPE_PATH)/rootfs-overlay/etc/init.d/S99ixope \
		$(TARGET_DIR)/etc/init.d/S99ixope
endef

$(eval $(generic-package))
