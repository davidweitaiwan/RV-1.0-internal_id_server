#!/usr/bin/bash
target_dir=$1

function PrintError () # Red
{
    error_color="\033[1;91m"
    reset_color="\033[0m"
    printf "${error_color}%s${reset_color}\n" "$1"
}

function PrintSuccess () # Green
{
    success_color="\033[1;92m"
    reset_color="\033[0m"
    printf "${success_color}%s${reset_color}\n" "$1"
}

function PrintWarning () # Yellow
{
    warn_color="\033[1;93m"
    reset_color="\033[0m"
    printf "${warn_color}%s${reset_color}\n" "$1"
}

# cd into $target_dir
CheckTargetPath ()
{
    if [ "$PWD" == "$1" ]
    then
        echo "In $1"
    else
        if ls $1 &> /dev/null
        then
            cd $1
            PrintWarning "Change directory: $PWD"
        else
            PrintError "Target path error: $1"
            return 1
        fi
    fi
    return 0
}

BackupRecover ()
{
    if ls $1.tmp &> /dev/null
    then
        cp $1.tmp $1
        PrintWarning "$1 recovered"
    else
        if ls $1 &> /dev/null
        then
            cp $1 $1.tmp
            PrintWarning "Backup $1: $1.tmp"
        else
            PrintError "$1 not found."
            return 1
        fi
    fi
    return 0
}

RunFunc ()
{
    # Check pwd
    CheckTargetPath $target_dir # Return 0 if succeed
    if [[ $? -eq 1 ]]
    then
        return 1
    fi

    # Install method goes here


    # Recover source_env.txt if .tmp exist
    BackupRecover source_env.txt
    if [[ $? -eq 1 ]]
    then
        return 1
    fi

    # Startup method goes here
    echo "python3 $PWD/RunIDServer.py" >> source_env.txt
}

RunFunc