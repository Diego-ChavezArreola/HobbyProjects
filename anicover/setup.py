from setuptools import setup
setup(
    name = 'anicover',
    version = '0.1.0',
    packages = ['anicover'],
    entry_points = {
        'console_scripts':[
            'anicover = anicover.__main__:main'
        ]
    }
)