#!/usr/bin/env bash
# A simplistic shortcut tool for changing dirs.
# Allows setting a root dir for your projects, and injects this on command invocation.
# The path is stored in a file at ~/.config/switch-to.conf.

function load_switch_to_config(){
    devel_path=$(cat ${HOME}/.config/switch-to.conf)
    if [[ $? == 1 ]]; then
        # File does not exist
        read -p "Could not find a switch-to.conf file. Setting it up now. Please specify your projects' root dir [~/devel]:\n" devel_path
        # store path in conf file (creating it if necessary)
        mkdir ${HOME}/.config
        cat >> ${HOME}/.config/switch-to.conf
    fi
    echo ${devel_path}
}

DEVEL_PATH=$(load_switch_to_config)
TARGET=${1}

cd ${DEVEL_PATH}/${TARGET}

