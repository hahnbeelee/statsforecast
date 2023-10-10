#!/usr/bin/env bash

for file in $(find _docs -type f -name "*mdx"); do
  echo ${file}
  sed -i '' -e 's/style="float:right; font-size:smaller"/style={{ float: "right", fontSize: "smaller" }}/g' $file
  sed -i '' -e 's/<br>/<br\/>/g' $file
done