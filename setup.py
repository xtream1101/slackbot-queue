from distutils.core import setup

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst', format='md')
except (IOError, ImportError) as e:
    print(str(e))
    long_description = ''

setup(
    name='slackbot-queue',
    packages=['slackbot_queue'],
    version='0.3.2',
    description='Slackbot with a celery queue for long running tasks',
    long_description=long_description,
    author='Eddy Hintze',
    author_email="eddy@hintze.co",
    url="https://github.com/xtream1101/slackbot-queue",
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    install_requires=['celery==4.1.0',
                      'slackclient==1.1.2'],
)
