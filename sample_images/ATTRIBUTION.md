# Sample image attribution

The demo images in this folder and in `frontend/public/samples/` are generated
by `scripts/generate_samples.py`. They are degraded (blurred, noised, etc.)
versions of the freely-licensed sample photographs that ship with
[scikit-image](https://scikit-image.org/), so they are safe to redistribute in a
public repository.

| Base image | Source | License |
|---|---|---|
| astronaut | Portrait of astronaut Eileen Collins (NASA), via `skimage.data.astronaut` | Public domain (NASA) |
| rocket | SpaceX Falcon 9 launch photograph, via `skimage.data.rocket` | Public domain (SpaceX released its imagery to the public domain) |
| chelsea | "Chelsea" the cat, by Stefan van der Walt, via `skimage.data.chelsea` | CC0 (released as a scikit-image test image) |

scikit-image itself is BSD-3-Clause and bundles these images specifically because
they are freely usable.

Note: the model is *trained* on Imagenette (an ImageNet subset), which is used
only locally at build time under ImageNet's non-commercial research terms and is
**not** redistributed in this repository (`ml/data/` is git-ignored). The demo
samples above deliberately use a different, redistributable source.
