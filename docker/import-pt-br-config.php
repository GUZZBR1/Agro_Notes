<?php

declare(strict_types=1);

use Drupal\Component\Serialization\Yaml;

$translations_directory = dirname(__DIR__) . '/modules/core/l10n_pt_br/config/pt-br';
$translated_storage = \Drupal::service('config.storage')->createCollection('language.pt-br');

foreach (glob($translations_directory . '/*.yml') as $file) {
  $config_name = basename($file, '.yml');
  $translation = Yaml::decode(file_get_contents($file));
  $translated_storage->write($config_name, $translation);
}

print "Imported farmOS Brazilian Portuguese configuration translations.\n";
