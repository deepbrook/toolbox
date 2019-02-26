#!/usr/bin/env bash
# Append an alias to your .bashrc. Also checks for existing aliases, and stops
# you from overwriting them.
# You must have a bashrc in your home directory (either at ~/.bashrc or
# ~/.config/bashrc).

ALIAS=$1
VALUE=$2

function fetch_bash_rc(){
    config_rc="${HOME}/.config/bashrc"
    home_rc="${HOME}/.bashrc"

    ls ${config_rc}
    if [[ $? == 0 ]] ; then
        echo ${config_rc}
        exit 0
    fi

    ls ${home_rc}
    if [[ $? == 0 ]] ; then
        echo ${home_rc}
        exit 0
    fi
    exit 1

}

function alias_is_unique() {
    alias=$1
    rc_path=$2
    cat ${rc_path} | grep "${alias}="
    if [[ $? == 1 ]]; then
        echo true
    else
        echo false
    fi
}

RC_PATH=$(fetch_bash_rc)
if [[ $? == 1 ]]; then
    echo "No bashrc found - are you using bash?"
    exit 1
fi

IS_UNIQUE=$(alias_is_unique ${ALIAS} ${RC_PATH})

if IS_UNIQUE; then
    echo "${ALIAS}=${VALUE}" >> ${RC_PATH}
fi

echo "$1=$2" >> ${rc_path}