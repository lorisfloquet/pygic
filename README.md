# `pygic`: Python .gitignore creator

`pygic` is a command line tool for generating gitignores. It is heavily inspired from gitignore.io and gig. Similar projects are `pygig` and `pygi`.

## Main differences with pygig

- `pygig` does not use the gitignores from gitignore.io.
- `pygig` requires `git` if we want to update its pre-downloaded gitignores.

## Main difference with pygi

- `pygi` cannot be used offline since it is a wrapper around the gitignore.io API.

## Main differences with gig

- `gig` is written in Go so it cannot be used as a Python library.
- `gig` requires `git` installed to download the gitignores from toptal/gitignore the first time it is ran.
- `gig` search functionality depends on `fzf`.
- `gig` can be easily installed on MacOS or if you have Go installed. Otherwise, you need to manually install its pre-built binaries.

## What makes pygic stand out

- All you need is `uv` installed, not even Python.
- `pygic` can be used offline as the gitignores from toptal/gitignore are pre-downloaded.
- You don't need `git` installed since cloning is handled by `dulwich`.
- The search functionality does not depend on `fzf`, but uses `pzp` which is a Python tool.

## Other remarks

- `pygic` does not support the `autogen` command from `gig` since it is experimental and I don't really see it much use.
- Similar to `gig`, the content of the gitignores match the ones from gitignore.io, except for the order of the stacks which is not standardized by gitignore.io. Here, we choose the alphabetical order.
- Finally `pygic` fixes what seems to be a small bug in gitignore.io's implementation where they remove all duplicated lines in the generated gitignores, even in comments. `pygic` only removes uncommented duplicated lines.

# Install

## uv

The easiest way to install `pygic` is to use `uv` as a Python tool manager. You can install `uv` with the following command:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For more information, check out `uv`'s [documentation](https://docs.astral.sh/uv/getting-started/installation/).  

Once `uv` is installed, all you have to do to install `pygic` as a CLI tool is:

```bash
uv tool install pygic
```

If you want to be able to update the gitignore by using the last ones on toptal/gitignore, you can install `pygic` with the [git] extra:

```bash
uv tool install pygic[git]
```

The [git] extra requires `git`. If you don't want to install `git`, you can still clone the toptal/gitignore repository thanks to `dulwich` (a Python implementation of `git`), with the [dulwich] extra:

```bash
uv tool install pygic[dulwich]
```

If you want to use `pygic search`, you can install `pygic` with the [search] extra:

```bash
uv tool install pygic[search]
```

Finally, if you want all extras, you can install `pygic` like this:

```bash
uv tool install pygic[extras]
```

# Usage

The usage is similar to `gig`.

## Generating a gitignore via available arguments

```
$ pygic gen Go Elm

### Elm ###
# elm-package generated files
elm-stuff
# elm-repl generated files
repl-temp-*

### Go ###
# Binaries for programs and plugins
...
```

## Using the search functionality

The search functionality allows you to search amongst the available arguments and finally generates a gitignore with the selected arguments.

```
$ pygic search
```

## Using the EXPERIMENTAL auto generate functionality

```
$ pygic autogen
```

## For more information, see

```
pygic --help
```

# Development

## uv

This project uses `uv` as virtual environment and package manager.

To contribute, all you have to do is, clone then:

```bash
uv venv
uv sync
```
