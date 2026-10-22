<?php

declare(strict_types=1);

namespace Drupal\data_stream\Hook;

use Drupal\Core\Database\Connection;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\data_stream\Entity\DataStreamInterface;

/**
 * Entity hook implementations for data_stream.
 */
class EntityHooks {

  public function __construct(
    protected Connection $connection,
  ) {}

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {
    if (!empty($entity_types['data_stream'])) {
      $entity_types['data_stream']->set('bundle_plugin_type', 'data_stream_type');
    }
  }

  /**
   * Implements hook_ENTITY_TYPE_delete().
   */
  #[Hook('data_stream_delete')]
  public function dataStreamDelete(DataStreamInterface $data_stream) {

    // If this is a "basic" data stream, delete data associated with it.
    if ($data_stream->bundle() == 'basic' && !empty($data_stream->id())) {
      $this->connection->delete('data_stream_basic')
        ->condition('id', $data_stream->id())
        ->execute();
    }
  }

}
