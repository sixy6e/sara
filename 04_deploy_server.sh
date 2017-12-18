#! /bin/bash
#
# SARA - Sentinel Australia Regional Access
#
# Deployment script
#
# Author : Jérôme Gasperi (https://github.com/jjrom)
# Date   : 2017.02.19
#
#

set -eu
set -o pipefail

CONFIG=
FORCE=NO
WWW_USER=nginx:nginx
PWD=`pwd`
SRC_DIR=`pwd`
function showUsage {
    echo ""
    echo "   SARA - Sentinel Australia Regional Access server deployment"
    echo ""
    echo "   Usage $0 [options]"
    echo ""
    echo "      -C | --config : local config file containing parameters to build config.php file"
    echo "      -F | --force : force suppression of endpoint directory (i.e. ${SARA_SERVER_TARGET_DIR}/${SARA_SERVER_VERSION_ENDPOINT} and ${SARA_CLIENT_TARGET_DIR})"
    echo "      -h | --help : show this help"
    echo ""
    echo ""
}

# Parsing arguments
while [[ $# > 0 ]]
do
	key="$1"

	case $key in
        -C|--config)
            CONFIG="$2"
            shift # past argument
            ;;
        -F|--force)
            FORCE=YES
            shift # past argument
            ;;
        -h|--help)
            showUsage
            exit 0
            shift # past argument
            ;;
            *)
        shift # past argument
        # unknown option
        ;;
	esac
done

if [ "${CONFIG}" == "" ]
then
    showUsage
    echo ""
    echo "   ** Missing mandatory config file ** ";
    echo ""
    exit 0
fi

# Source config file
. ${CONFIG}

# Set endpoints
SARA_SERVER_ENDPOINT=${SARA_SERVER_TARGET_DIR}${SARA_SERVER_VERSION_ENDPOINT}

if [ "${FORCE}" == "YES" ]
then
  echo " ==> Suppress ${SARA_SERVER_ENDPOINT}"
  rm -Rf ${SARA_SERVER_ENDPOINT}
fi

mkdir -p ${SARA_SERVER_TARGET_DIR}

echo " ==> Deploy resto in ${SARA_SERVER_ENDPOINT}"
${SRC_DIR}/resto/_install/deploy.sh -s ${SRC_DIR}/resto -t ${SARA_SERVER_ENDPOINT}

# Fix RewriteBase path
ESCAPED_SARA_PATH=$(echo "${SARA_SERVER_SUB}${SARA_SERVER_VERSION_ENDPOINT}" | sed -r -e 's/\//\\\//g')
sed -i -r -e "s/\/resto\//${ESCAPED_SARA_PATH}\//g" ${SARA_SERVER_ENDPOINT}/.htaccess

echo " ==> Copy models under ${SARA_SERVER_ENDPOINT}/include/resto/Models"
cp -R ${SRC_DIR}/sara.server/Models/*.php ${SARA_SERVER_ENDPOINT}/include/resto/Models/

echo " ==> Use ${CONFIG} file to generate ${SARA_SERVER_ENDPOINT}/include/config.php";
${SRC_DIR}/sara.server/generate_config.sh -C ${CONFIG} > ${SARA_SERVER_ENDPOINT}/include/config.php
chmod 0600 ${SARA_SERVER_ENDPOINT}/include/config.php

echo " ==> Set ${SARA_SERVER_ENDPOINT} rights to ${WWW_USER}"
chown -R ${WWW_USER} ${SARA_SERVER_ENDPOINT}

echo " ==> Create property mappings for collections"

curl_cmd=("curl" "--silent" "--show-error" "--fail" "--header" "Host: ${SARA_SERVER_URL}")
[ "${SERVER_PROTOCOL}" == "https" ] && curl_cmd+=("-k")

api_base_url="${SERVER_PROTOCOL}://${RESTO_ADMIN_USER}:${RESTO_ADMIN_PASSWORD}@localhost${SARA_SERVER_SUB}${SARA_SERVER_VERSION_ENDPOINT}"

if [ -n "${EXTERNAL_DATA_HOST}" ] ; then
  quicklook_base_url="${SERVER_PROTOCOL}://${EXTERNAL_DATA_HOST}${DATA_ROOT_URL_PATH}"
  resource_base_url="${SERVER_PROTOCOL}://${EXTERNAL_DATA_HOST}${DATA_ROOT_URL_PATH}"
else
  quicklook_base_url="${SERVER_PROTOCOL}://${SARA_SERVER_URL}${DATA_ROOT_URL_PATH}"
  resource_base_url="${DATA_ROOT_DIR}"
fi

for i in {1..3};do
  coll_id="S${i}"
  src_path=${SRC_DIR}/sara.server/collections/"${coll_id}.json";
  out_path=${SRC_DIR}/sara.server/collections/"SARA-${coll_id}.json";
  jq ".propertiesMapping = {
    \"quicklook\": \"${quicklook_base_url}/Sentinel-${i}{:resource:}/{:productIdentifier:}.png\",
    \"resource\": \"${resource_base_url}/Sentinel-${i}{:resource:}/{:productIdentifier:}.zip\"
  } | .propertiesMapping.thumbnail = .propertiesMapping.quicklook" ${src_path} >${out_path}

  echo " ==> Install ${coll_id} collection"
  if "${curl_cmd[@]}" "${api_base_url}/api/collections/${coll_id}/describe.json" &>/dev/null ; then
    if [ "${FORCE}" == "YES" ] ; then
      echo "Updating existing collection"
      "${curl_cmd[@]}" -X PUT -H "Content-Type: application/json" -d @${out_path} "${api_base_url}/collections/${coll_id}"
      echo ""
    else
      echo "Already exists -- skipped"
    fi
  else
    echo "Creating new collection"
    "${curl_cmd[@]}" -X POST -H "Content-Type: application/json" -d @${out_path} "${api_base_url}/collections"
    echo ""
  fi
  touch "${out_path}.ok"
done

echo " Done !"
