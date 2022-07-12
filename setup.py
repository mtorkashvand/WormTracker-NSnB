import setuptools

requirements = [
    'docopt',
    'numpy',
    'pyzmq'
]

console_scripts = [
    'wormtracker_client=wormtracker_scope.zmq.client:main',
    'wormtracker_forwarder=wormtracker_scope.zmq.forwarder:main',
    'wormtracker_hub=wormtracker_scope.devices.hub_relay:main',
    'wormtracker_publisher=wormtracker_scope.zmq.publisher:main',
    'wormtracker_server=wormtracker_scope.zmq.server:main',
    'wormtracker_subscriber=wormtracker_scope.zmq.subscriber:main',
    'wormtracker_logger=wormtracker_scope.devices.logger:main',
    'wormtracker_displayer=wormtracker_scope.devices.displayer:main',
    'wormtracker_data_hub=wormtracker_scope.devices.data_hub:main',
    'wormtracker_writer=wormtracker_scope.devices.writer:main',
    'wormtracker_processor=wormtracker_scope.devices.processor:main',
    'wormtracker_commands=wormtracker_scope.devices.commands:main',
    'wormtracker_tracker=wormtracker_scope.devices.tracker:main',
    'wormtracker=wormtracker_scope.system.wormtracker:main',
    'wormtracker_teensy_commands=wormtracker_scope.devices.teensy_commands:main'
]

setuptools.setup(
    name="wormtracker_scope",
    version="0.0.1",
    author="Mahdi Torkashvand",
    author_email="mmt.mahdi@gmail.com",
    description="Software to operate wormtracker.",
    url="https://github.com/venkatachalamlab/wormtracker",
    project_urls={
        "Bug Tracker": "https://github.com/venkatachalamlab/wormtracker/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows :: Windows 10",
    ],
    entry_points={
        'console_scripts': console_scripts
    },
    packages=['wormtracker_scope'],
    python_requires=">=3.6",
)
