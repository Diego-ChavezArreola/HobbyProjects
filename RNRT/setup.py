import setuptools 

setuptools.setup( 
    name='reani', 
    version='0.1.0', 
    author='Baker', 
    description='Renames anime subs in database', 
    packages=setuptools.find_packages(), 
    entry_points={ 
        'console_scripts': [ 
            'reani = reani.reani:main' 
        ] 
    }, 
    classifiers=[ 
        'Programming Language :: Python :: 3', 
        'License :: OSI Approved :: MIT License', 
        'Operating System :: OS Independent', 
    ], 
)