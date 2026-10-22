<?php

declare(strict_types=1);

namespace Drupal\asset\Entity;

use Drupal\Core\Config\Entity\ConfigEntityBundleBase;
use Drupal\Core\Entity\Attribute\ConfigEntityType;
use Drupal\Core\Entity\EntityDeleteForm;
use Drupal\Core\Entity\EntityViewBuilder;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\asset\AssetTypeListBuilder;
use Drupal\asset\Form\AssetTypeForm;
use Drupal\entity\Routing\DefaultHtmlRouteProvider;

/**
 * Defines the asset type entity.
 */
#[ConfigEntityType(
  id: 'asset_type',
  label: new TranslatableMarkup('Asset type'),
  label_collection: new TranslatableMarkup('Asset types'),
  label_singular: new TranslatableMarkup('Asset type'),
  label_plural: new TranslatableMarkup('Asset types'),
  config_prefix: 'type',
  entity_keys: [
    'id' => 'id',
    'label' => 'label',
    'uuid' => 'uuid',
  ],
  handlers: [
    'list_builder' => AssetTypeListBuilder::class,
    'view_builder' => EntityViewBuilder::class,
    'form' => [
      'add' => AssetTypeForm::class,
      'edit' => AssetTypeForm::class,
      'delete' => EntityDeleteForm::class,
    ],
    'route_provider' => [
      'default' => DefaultHtmlRouteProvider::class,
    ],
  ],
  links: [
    'canonical' => '/admin/structure/asset-type/{asset_type}',
    'add-form' => '/admin/structure/asset-type/add',
    'edit-form' => '/admin/structure/asset-type/{asset_type}/edit',
    'delete-form' => '/admin/structure/asset-type/{asset_type}/delete',
    'collection' => '/admin/structure/asset-type',
  ],
  admin_permission: 'administer asset types',
  bundle_of: 'asset',
  label_count: [
    'singular' => '@count asset type',
    'plural' => '@count asset types',
  ],
  config_export: [
    'id',
    'label',
    'description',
    'new_revision',
  ],
)]
class AssetType extends ConfigEntityBundleBase implements AssetTypeInterface {

  /**
   * The asset type ID.
   *
   * @var string
   */
  protected $id;

  /**
   * The asset type label.
   *
   * @var string
   */
  protected $label;

  /**
   * A brief description of this asset type.
   *
   * @var string
   */
  protected $description;

  /**
   * Default value of the 'Create new revision' checkbox of the asset type.
   *
   * @var bool
   */
  protected $new_revision = TRUE;

  /**
   * {@inheritdoc}
   */
  public function getDescription() {
    return $this->description;
  }

  /**
   * {@inheritdoc}
   */
  public function setDescription($description) {
    return $this->set('description', $description);
  }

  /**
   * {@inheritdoc}
   */
  public function shouldCreateNewRevision() {
    return $this->new_revision;
  }

  /**
   * {@inheritdoc}
   */
  public function setNewRevision($new_revision) {
    return $this->set('new_revision', $new_revision);
  }

}
