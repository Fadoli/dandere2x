#!/bin/bash

# this file will compile and move the 
# dandere2x_cpp binary to the correct
# default path. obviously by the name
# of this file, this is Linux/sh only

# note this have a few dependencies
# mostly cmake, make and a compiler
# I don't know much about these tbh

# you should have them by defaults
# I can say that for an Arch based 
# system everything is in the base
# devel package and for Ubuntu sys
# the package build-essential IIRC

# the script auto cds into its root path
# so you can run this from outside paths
# without any problem and it should work

# to run this script "sh build_linux.sh"

match () {
    if [[ "$1" =~ "$2" ]]; then
        echo "true"
    else
        echo "false"
    fi;
}

recommend_install () {
    local distribution=$(uname -a)

    # Bash 4.0 lower case
    distribution=${distribution,,}

    local isArch=$(match "$distribution" "arch")
    local isUbuntu=$(match "$distribution" "ubuntu")
    local isDebian=$(match "$distribution" "debian")

    if [ "$isArch" = "true" ]; then
        echo -e "Please install devel packages"
        return
    elif [ "$isUbuntu" = "true" ] || [ "$isDebian" = "true" ] ; then
        echo -e "Please install build-essential\nYou can run : 'sudo apt-get install build-essential'"
        return
    else
        echo -e "Your linux distribution has no recommanded install...\nFeel free to add support for yours ($distribution)"
    fi;
}

verify_dep () {
    local hasMake=$(match "$(which make)" "make")
    local hasGcc=$(match "$(which g++)" "g++")
    local hasClang=$(match "$(which clang)" "clang")

    local hasFailed="false"

    if [ "$hasMake" = "false" ]; then
        echo "Missing make command"
        recommend_install
        hasFailed="true"
    fi;
    if [ "$hasGcc" = "false" ] && [ "$hasClang" = "false"]; then
        echo "Missing either g++ or clang"
        recommend_install
        hasFailed="true"
    fi;
    if [ "$hasFailed" = "false" ]; then
        echo "Seems like you're ready to install !"
    else
        exit 1;
    fi;
}

verify_dep

DIRECTORY=$(cd `dirname $0` && pwd)

cd $DIRECTORY

mkdir -p externals

cd dandere2x_cpp

cmake CMakeLists.txt
make -j$(nproc)

mv ../dandere2x_cpp/dandere2x_cpp ../src/externals/dandere2x_cpp

echo -e "\n\nDONE !"
