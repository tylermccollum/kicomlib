# KiComLib  

This [KiCad EDA](https://www.kicad.org/) plugin utilizes the new KiCad database and http library feature and extends it with a web component to manage part data like part numbers, manufacturers, distributor order numbers. It requires an Instance of https://heronitec-solutions.github.io/KiComLibServer/ .

## Web Component 

To use this plugin you need the KiComLib web component. It can be found on [Docker Hub](https://hub.docker.com/r/heronitecsolutions/kicomlib-server) and [GitLab](https://heronitec-solutions.github.io/KiComLibServer/).

## Installation

### Automated, via KiCad plugin manager

The KiComLib plugin is part of the official KiCad repository. You can install it via the Plugin an Content Manager in KiCad.

### Manual, most current version

To get the most current version of the plugin, clone the repo in the plugin directory of your KiCad installtion:

```bash
# Linux (KiCad from Ubuntu PPA)
cd <HOME>/.local/share/kicad/10.0/3rdparty/plugins
# Linux (KiCad 10 from FlatPak)
cd <HOME>/.var/app/org.kicad.KiCad/data/kicad/10.0/3rdparty/plugins
# Windows
cd C:\Users\<USERNAME>\Documents\KiCad\10.0\3rdparty\plugins
# Mac
cd <HOME>/Documents/KiCad/10.0/3rdparty/plugins

# then clone the repo main branch
git clone --depth 1 https://github.com/heronitec-solutions/kicomlib
```

Restart KiCad and it should be visiable.

## Manual, latest stable release

Same as above, but instead cloning the main branch, clone the realease branch:

```bash
# clone the repo tag
git clone --depth 1 --branch release https://github.com/heronitec-solutions/kicomlib
```

### Manual, older version

Same as above, but instead cloning the main branch, clone the desired tag:

```bash
# clone the repo tag
git clone --depth 1 --branch v2.0.1 https://github.com/heronitec-solutions/kicomlib
```

## Embedded 3D models

Footprint references using `kicad-embed://` keep their original URI, embedded
payload, and placement during synchronization. Embedded models need no separate
server model record. External model paths still use the configured model
directory; footprints with both kinds retain their original model positions.

If an older client uploaded an embedded reference as
`${PLACEHOLDER}/kicad-embed:/...`, update the client and sync the correct local
footprint again. This creates a corrected revision without rewriting history.
The client does not automatically repair already-damaged server copies.

## Known Problems

### Plugin icon position

At the moment (KiCad v10.0) it's only possible to display a plugin icon in the PCB editor. We will move it to the symbol and footprint editor when the required KiCad feature is available ([KiCad Issue 19418](https://gitlab.com/kicad/code/kicad/-/issues/19418))

### Missing Paths / Libraries

KiComLib tries to add the required KiCad environment paths and libraries automatically. Because there is no cli method for that yet, KiComLib modifies the setting files manually. This sometimes fails when KiCad does work with the files at the same time. If you are missing paths or libraries, you can crate it manually.

#### Adding Paths manually

For each Library it should create the following paths:

*{lib_path_key}*_BASE_PATH
*{lib_path_key}*_3DMODEL_DIR
*{lib_path_key}*_DATASHEET_DIR
*{lib_path_key}*_FOOTPRINT_DIR
*{lib_path_key}*_SYMBOL_DIR
*{lib_path_key}*_TEMPLATE_DIR

(Replace *{lib_path_key}* with your selected Path Key fot the library)

#### Adding HTTP Library manually

After that the HTTP-Library can be added (as a symbol library):

**Nickname:** *{lib_path_name}*
**Library Path:** ${*{lib_path_key}*_BASE_PATH}/HttpLibrary.kicad_httplib
**Library Fomat:** HTTP
