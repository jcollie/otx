from setuptools import setup, find_packages
import version
setup(
    name = 'otx',
    version = version.getVersion(),
    packages = find_packages(),
    package_data = {'otx': ['amqp/*.xml']}
)
