// The DOI in data/release.json is Zenodo's all-versions DOI: it always leads to the newest version deposited there, which is `archivedVersion`.
// Every page, file and draft that prints the DOI next to a version number takes its wording from here, so none of them implies that the current version is deposited when it is not.
export function doiWording(release) {
  const current = release.archivedVersion === release.version;
  const url = `https://doi.org/${release.doi}`;
  const aside = current ? "" : `the newest version deposited there is v${release.archivedVersion}; v${release.version} is not deposited yet`;
  return {
    current, url, aside, archived: release.archivedVersion,
    // plain-text citation used by the copy button, the structured data and the drafts
    cite: (author, year, title) => `${author} (${year}). ${title} (v${release.version}). Zenodo${current ? "" : ", all versions"}. ${url}${current ? "" : ` (${aside})`}`,
  };
}
