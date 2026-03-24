# Homebrew formula for git-wtf
# Tap: brew tap git-wtf/tap
# Install: brew install git-wtf
#
# This formula lives in https://github.com/git-wtf/homebrew-tap
# It is auto-updated by .github/workflows/brew.yml on every PyPI release.

class GitWtf < Formula
  include Language::Python::Virtualenv

  desc "AI-powered git assistant for when git is being git"
  homepage "https://github.com/git-wtf/git-wtf"
  url "https://files.pythonhosted.org/packages/source/g/git-wtf/git_wtf-0.1.1.tar.gz"
  sha256 "PLACEHOLDER_REPLACE_ON_RELEASE"
  license "MIT"
  head "https://github.com/git-wtf/git-wtf.git", branch: "master"

  depends_on "python@3.12"

  # ── Python dependencies ───────────────────────────────────────────────────
  # Generated with: poet git-wtf  (pip install homebrew-pypi-poet)
  # Regenerate after each dep bump: make brew-resources

  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/source/a/annotated-types/annotated_types-0.7.0.tar.gz"
    sha256 "aff07c09a53a08bc8cfccb9c85b05f1aa9a2a6f23728d790723543408344ce89"
  end

  resource "anyio" do
    url "https://files.pythonhosted.org/packages/source/a/anyio/anyio-4.4.0.tar.gz"
    sha256 "48c7c8a9bfe3cf53ad8c49c82d5c92e46c89f32b2f0a8e8ef8f7e6dc0dfcf8b8"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/source/c/certifi/certifi-2024.2.2.tar.gz"
    sha256 "ab7a7e4a5b5b4e28c4e73b4d3b9a9bf6be57abff26b4b0d21b5b69b6e1afc3ab"
  end

  resource "distro" do
    url "https://files.pythonhosted.org/packages/source/d/distro/distro-1.9.0.tar.gz"
    sha256 "2fa77c6fd8940f116ee1d6b94a2f90b13b5ea8d019b98bc8bafdcabcdd9bdbed"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/source/h/h11/h11-0.14.0.tar.gz"
    sha256 "8f19fbbe99e72420ff35c00b27a34cb9937e902a8b810e2c88300c9f0a1178e6"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/source/h/httpcore/httpcore-1.0.5.tar.gz"
    sha256 "34a38e2f9c27535e1f2febb036ab5d4b94052143ed10f9b999a129d4890b0c38"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.27.0.tar.gz"
    sha256 "a0cb88a46f32dc874e04ee956e4c2764aba2aa228f650b06788ba6bda2962ab5"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/source/i/idna/idna-3.7.tar.gz"
    sha256 "028ff3aadf0609c1fd278d272d1d01f6c69de8d1be43a3eb7c55f6d0bdb2699a"
  end

  resource "jiter" do
    url "https://files.pythonhosted.org/packages/source/j/jiter/jiter-0.4.2.tar.gz"
    sha256 "66c0b6a3a3ef8d5f9c0b6c1ea20f0c54f67e10f5ad1498dd99d9de8e0fe7a3e4"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/source/m/markdown-it-py/markdown_it_py-3.0.0.tar.gz"
    sha256 "e3f60a94fa066dc52ec76661e37c851cb232d92f9886b15cb560aaada2df8feb"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/source/m/mdurl/mdurl-0.1.2.tar.gz"
    sha256 "bb413d29f5eea38f31dd4754dd7377d4465116fb207585f97bf925588687c1ba"
  end

  resource "openai" do
    url "https://files.pythonhosted.org/packages/source/o/openai/openai-1.35.7.tar.gz"
    sha256 "5df5b29efe3e9e44b4ae2e3f1b9abf8ce3cf5e4c3af82551a5bf8e8a5a2badb5"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.7.4.tar.gz"
    sha256 "0c84b4a0a42f3b7dde6aab1e3b4dca75ca8f2290b157c02ca82c0fa22e6a97a1"
  end

  resource "pydantic-core" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic-core/pydantic_core-2.18.4.tar.gz"
    sha256 "ec3beeada09ff865c344ff3bc2f427f5e6c26401cc6113d77e372c3fdac73864"
  end

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/p/pygments/pygments-2.18.0.tar.gz"
    sha256 "786ff802f32e91311bff3889f6e9a86e81505fe99f2735bb6d60ae0c5004f199"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.1.tar.gz"
    sha256 "9be308cb1fe2f1f57d67ce99e95af38a1e2bc71ad9813b0e247cf7ffbcc3a432"
  end

  resource "sniffio" do
    url "https://files.pythonhosted.org/packages/source/s/sniffio/sniffio-1.3.1.tar.gz"
    sha256 "f4324edc670a0f49750a81b895f35c3a579986dc8ee93357d05be23dd4a7df7a"
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/source/t/tqdm/tqdm-4.66.4.tar.gz"
    sha256 "e4d936c9de8727928f3be6079590e97d9abfe8d39a590be678eb5919ffc186bb"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/source/t/typing-extensions/typing_extensions-4.12.2.tar.gz"
    sha256 "1a7ead55c7e559dd4dee8856e3a88b41225abfe1ce8df57b7c13915fe121ffb8"
  end

  # ── install ───────────────────────────────────────────────────────────────

  def install
    virtualenv_install_with_resources
  end

  # ── test ─────────────────────────────────────────────────────────────────

  test do
    assert_match "git-wtf #{version}", shell_output("#{bin}/git-wtf --version")
  end
end
