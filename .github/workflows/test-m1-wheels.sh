#!/bin/zsh

# Show commands being executed
set -x
# Fail if a command fails
set -e

# Get Python client tests
git clone --recurse-submodules "https://github.com/aerospike/aerospike-client-python.git"
cd aerospike-client-python/

# Prepare for testing wheels
python3 -m pip install delocate

openssl_path=$(brew --prefix openssl@1.1)
export SSL_LIB_PATH="$openssl_path/lib/"
export CPATH="$openssl_path/include/"
export STATIC_SSL=1

# Helper functions

# set_tag() {
#     resource_endpoint="$1"
#     resource_id=$(curl -w '\n' -s $resource_endpoint)
#     aws ec2 create-tags --resources "$resource_id" --tags Key=testdestroy,Value=""
# }

# raise_flags() {
#     # Set flags to destroy dedicated host of this instance
#     set_tag http://169.254.169.254/latest/meta-data/placement/host-id
#     # and the instance itself
#     set_tag http://169.254.169.254/latest/meta-data/instance-id
# }

# Build and test wheels for each python version
serverIp=$1
sed -i '.bak' "s/hosts: 127.0.0.1:3000/hosts: $serverIp:3000/" test/config.conf
python_versions=('3.8' '3.9' '3.10')
for version in "${python_versions[@]}"; do
    brew install python@${version}

    python${version} -m pip install build
    python${version} -m build

    # Fix wheel
    delocate-wheel --require-archs "arm64" -w wheelhouse/ -v dist/*.whl

    # Install wheel
    python${version} -m pip install --find-links=wheelhouse/ --no-index aerospike

    pushd test/
    python${version} -m pip install -r requirements.txt
    python${version} -m pytest new_tests/

    # Fail this workflow if the tests failed
    result=$(echo $?)
    if [[ $result -ne 0 ]]; then
        # raise_flags
        exit $result
    fi

    # Cleanup for next build
    popd
    rm -r dist/
done

# All wheels passed
# so send to artifactory and self destruct this instance
# raise_flags
