from setuptools import setup, find_packages

setup(
    name='aks-ip-diagnostic',
    version='0.1.0',
    author='Azer',
    author_email='taboubi.azer@gmail.com',
    description='A diagnostic tool for Azure Kubernetes Service to identify IP exhaustion issues.',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'azure-mgmt-containerservice',
        'azure-mgmt-network',
        'pyyaml',
        'requests',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)