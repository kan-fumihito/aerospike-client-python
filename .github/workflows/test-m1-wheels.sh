#!/bin/zsh

# Show commands being executed
set -x

# Get Python client source
git clone --recurse-submodules "https://github.com/aerospike/aerospike-client-python.git"
cd aerospike-client-python/

# Prepare for building wheels
brew install python@3.8
brew install python@3.9
python3.9 -m pip install delocate

openssl_install_path=$(brew --prefix openssl@1.1)
export STATIC_SSL=1
export SSL_LIB_PATH="$openssl_install_path/lib/"
export CPATH="$openssl_install_path/include/"

# Helper functions

set_tag() {
    resource_endpoint="$1"
    resource_id=$(curl -w '\n' -s $resource_endpoint)
    aws ec2 create-tags --resources "$resource_id" --tags Key=testdestroy,Value=""
}

raise_flags() {
    # Set flags to destroy dedicated host of this instance
    set_tag http://169.254.169.254/latest/meta-data/placement/host-id
    # and the instance itself
    set_tag http://169.254.169.254/latest/meta-data/instance-id
}

# Build wheels for each python version
python_versions=('3.8' '3.9')
for version in "${python_versions[@]}"; do
    python${version} -m pip install build
    python${version} -m build
    delocate-wheel --require-archs "arm64" -w wheelhouse/ -v dist/*.whl
    python${version} -m pip install wheelhouse/*.whl

    cd test/
    sed -i "s/hosts : 127.0.0.1:3000/hosts : ${{ env.SERVER_IP }}/" config.conf
    python${version} -m pip install -r requirements.txt
    python${version} -m pytest new_tests/

    # Fail this workflow if the tests failed
    result=$(echo $?)
    if [[ $result -ne 0 ]]; then
        raise_flags
        exit $result
    fi
    cd ..
done

# All wheels passed so self destruct this instance
raise_flags
