<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv\Hook;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Session\AccountInterface;
use Drupal\farm_import_csv\Access\CsvImportMigrationAccess;
use Drupal\file\FileUsage\FileUsageInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * File hook implementations for farm_import_csv.
 */
class FileHooks {

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
    protected FileUsageInterface $fileUsage,
    protected AccountInterface $currentUser,
    #[Autowire(service: 'farm_import_csv.access')]
    protected CsvImportMigrationAccess $csvImportMigrationAccess,
  ) {}

  /**
   * Implements hook_file_download().
   */
  #[Hook('file_download')]
  public function fileDownload($uri) {

    // Look up the file entity.
    $files = $this->entityTypeManager->getStorage('file')->loadByProperties([
      'uri' => $uri,
    ]);
    $file = reset($files) ?: NULL;

    // If a file was not found, return NULL.
    if (is_null($file)) {
      return NULL;
    }

    // Get file usage.
    $usages = $this->fileUsage->listUsage($file);

    // If the file was not uploaded by farm_import_csv, return NULL.
    if (!array_key_exists('farm_import_csv', $usages)) {
      return NULL;
    }

    // Get the migration ID.
    $migration_id = array_key_first($usages['farm_import_csv']['migration']);

    // If the current user uploaded the file, or if the current user has access
    // to the migration that imported it, allow access.
    $access = $this->csvImportMigrationAccess->access($this->currentUser, $migration_id);
    if ($file->getOwnerId() === $this->currentUser->id() || $access->isAllowed()) {
      return [
        'Content-Type' => 'application/csv',
        'Content-disposition' => 'attachment; filename="' . $file->getFilename() . '"',
      ];
    }

    // Otherwise, deny access.
    return -1;
  }

}
