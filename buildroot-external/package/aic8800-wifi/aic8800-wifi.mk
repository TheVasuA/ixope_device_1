################################################################################
#
# aic8800-wifi — AIC8800 SDIO WiFi driver (out-of-tree kernel module)
#
################################################################################

AIC8800_WIFI_VERSION = 6ec370a
AIC8800_WIFI_SITE = $(call github,radxa-pkg,aic8800,$(AIC8800_WIFI_VERSION))
AIC8800_WIFI_LICENSE = GPL-2.0+
AIC8800_WIFI_LICENSE_FILES = LICENSE

# Driver source is under src/SDIO/driver_fw/driver/aic8800/
AIC8800_WIFI_MODULE_SUBDIRS = src/SDIO/driver_fw/driver/aic8800

# Tell kbuild to build these as modules
# Override platform flags — we cross-compile, not native Ubuntu build
# CONFIG_USE_FW_REQUEST=y makes the driver use request_firmware() to load
# firmware from /lib/firmware/ instead of an empty built-in array.
# Skip btlpm (no Bluetooth needed on this device).
AIC8800_WIFI_MODULE_MAKE_OPTS = \
	CONFIG_AIC8800_BTLPM_SUPPORT=n \
	CONFIG_AIC8800_WLAN_SUPPORT=m \
	CONFIG_AIC_WLAN_SUPPORT=m \
	CONFIG_PLATFORM_UBUNTU=n \
	CONFIG_PLATFORM_ROCKCHIP=n \
	CONFIG_PLATFORM_ALLWINNER=n \
	CONFIG_PLATFORM_AMLOGIC=n \
	CONFIG_USE_FW_REQUEST=y \
	KDIR=$(LINUX_DIR)

$(eval $(kernel-module))
$(eval $(generic-package))

# Install firmware files to target
define AIC8800_WIFI_INSTALL_TARGET_CMDS
	# The chip identifies as AIC8800D80 (chip rev 7).
	# Driver looks for firmware in /lib/firmware/aic8800D80/
	# Install ALL firmware variants to cover all chip revisions.
	for dir in aic8800 aic8800D80 aic8800D80N aic8800D80X2 aic8800DC; do \
		if [ -d $(@D)/src/SDIO/driver_fw/fw/$$dir ]; then \
			mkdir -p $(TARGET_DIR)/lib/firmware/$$dir ; \
			cp -a $(@D)/src/SDIO/driver_fw/fw/$$dir/* \
				$(TARGET_DIR)/lib/firmware/$$dir/ ; \
		fi ; \
	done

	# Also install the AIC common firmware from the aic/ directory if present
	if [ -d $(@D)/src/SDIO/driver_fw/aic ]; then \
		mkdir -p $(TARGET_DIR)/lib/firmware/aic8800D80 ; \
		cp -a $(@D)/src/SDIO/driver_fw/aic/* \
			$(TARGET_DIR)/lib/firmware/aic8800D80/ 2>/dev/null || true ; \
	fi
endef
