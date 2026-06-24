################################################################################
#
# aic8800-wifi — AIC8800 SDIO WiFi driver (out-of-tree kernel module)
#
################################################################################

AIC8800_WIFI_VERSION = d5e11d4b9166d4159ffb4d4baadfcdb07d482e20
AIC8800_WIFI_SITE = $(call github,radxa-pkg,aic8800,$(AIC8800_WIFI_VERSION))
AIC8800_WIFI_LICENSE = GPL-2.0+
AIC8800_WIFI_LICENSE_FILES = LICENSE

# Driver source is under src/SDIO/driver_fw/driver/aic8800/
AIC8800_WIFI_MODULE_SUBDIRS = src/SDIO/driver_fw/driver/aic8800

# Tell kbuild to build these as modules
# Override platform flags — we cross-compile, not native Ubuntu build
AIC8800_WIFI_MODULE_MAKE_OPTS = \
	CONFIG_AIC8800_BTLPM_SUPPORT=m \
	CONFIG_AIC8800_WLAN_SUPPORT=m \
	CONFIG_AIC_WLAN_SUPPORT=m \
	CONFIG_PLATFORM_UBUNTU=n \
	CONFIG_PLATFORM_ROCKCHIP=n \
	CONFIG_PLATFORM_ALLWINNER=n \
	CONFIG_PLATFORM_AMLOGIC=n \
	KDIR=$(LINUX_DIR)

$(eval $(kernel-module))
$(eval $(generic-package))

# Install firmware files to target
define AIC8800_WIFI_INSTALL_TARGET_CMDS
	# Install all firmware variants the driver may request
	mkdir -p $(TARGET_DIR)/lib/firmware/aic8800
	mkdir -p $(TARGET_DIR)/lib/firmware/aic8800D80
	mkdir -p $(TARGET_DIR)/lib/firmware/aic8800DC

	# aic8800 base firmware
	if [ -d $(@D)/src/SDIO/driver_fw/fw/aic8800 ]; then \
		cp -a $(@D)/src/SDIO/driver_fw/fw/aic8800/* \
			$(TARGET_DIR)/lib/firmware/aic8800/ ; \
	fi

	# aic8800D80 firmware (common on Radxa Zero 3W rev2+)
	if [ -d $(@D)/src/SDIO/driver_fw/fw/aic8800D80 ]; then \
		cp -a $(@D)/src/SDIO/driver_fw/fw/aic8800D80/* \
			$(TARGET_DIR)/lib/firmware/aic8800D80/ ; \
	fi

	# aic8800DC firmware
	if [ -d $(@D)/src/SDIO/driver_fw/fw/aic8800DC ]; then \
		cp -a $(@D)/src/SDIO/driver_fw/fw/aic8800DC/* \
			$(TARGET_DIR)/lib/firmware/aic8800DC/ ; \
	fi
endef
